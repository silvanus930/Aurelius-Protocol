import concurrent.futures
import logging
import signal
import socket
import time
from pathlib import Path
from typing import Tuple  # noqa: UP035 — bittensor SDK requires typing.Tuple

import bittensor as bt

import aurelius
from aurelius.common.version import PROTOCOL_VERSION
from aurelius.config import Config
from aurelius.miner.config_store import ConfigStore
from aurelius.miner.work_token import generate_work_id
from aurelius.protocol import ScenarioConfigSynapse

logger = logging.getLogger(__name__)


class Miner:
    def __init__(self):
        self.config = Config
        self.should_exit = False

        # Warn if wallet is still on defaults (easy identity collision)
        if self.config.WALLET_NAME == "default" and self.config.WALLET_HOTKEY == "default":
            logger.warning(
                "WALLET_NAME and WALLET_HOTKEY are both 'default'. "
                "Set explicit wallet names to avoid identity collisions between operators."
            )

        # Guard against TESTLAB_MODE on mainnet — disables validator-permit
        # checks, allowing any registered hotkey to query the miner (CS-H2).
        if self.config.TESTLAB_MODE and self.config.NETWORK == "finney":
            raise RuntimeError(
                "TESTLAB_MODE=1 is not allowed on mainnet (finney). "
                "This disables validator-permit checks and exposes the miner to "
                "unauthorized queries. Remove TESTLAB_MODE or set ENVIRONMENT=testnet."
            )

        self.wallet = bt.Wallet(name=self.config.WALLET_NAME, hotkey=self.config.WALLET_HOTKEY)
        self.subtensor = bt.Subtensor(network=self.config.NETWORK)
        self.metagraph = bt.Metagraph(
            netuid=self.config.NETUID,
            network=self.config.NETWORK,
            subtensor=self.subtensor,
        )

        config_dir = self.config.MINER_CONFIG_DIR
        if not Path(config_dir).is_dir():
            raise ValueError(
                f"MINER_CONFIG_DIR={config_dir!r} does not exist. "
                "Create the directory and add scenario JSON files, or set MINER_CONFIG_DIR to an existing path."
            )
        self.config_store = ConfigStore(config_dir)
        logger.info("Config store: %d configs loaded from %s", self.config_store.count, config_dir)

        external_ip = self.config.AXON_EXTERNAL_IP
        if external_ip == "auto":
            external_ip = self._detect_external_ip()
            logger.info("Auto-detected external IP: %s", external_ip)

        self.axon = bt.Axon(
            wallet=self.wallet,
            port=self.config.AXON_PORT,
            external_ip=external_ip,
            external_port=self.config.AXON_EXTERNAL_PORT,
        )
        self.axon.attach(forward_fn=self.forward, blacklist_fn=self.blacklist)
        # Catch-all handler so we can log non-ScenarioConfig requests too.
        # Bittensor dispatches by synapse type; ScenarioConfigSynapse still
        # uses the dedicated handler above.
        self.axon.attach(forward_fn=self.forward_any, blacklist_fn=self.blacklist_any)

        logger.info("Serving axon on netuid %d, port %d", self.config.NETUID, self.config.AXON_PORT)
        self.axon.serve(netuid=self.config.NETUID, subtensor=self.subtensor)
        self.axon.start()

        logger.info("Miner started | wallet=%s hotkey=%s", self.wallet.name, self.wallet.hotkey_str)

        # Fetch and display deposit address for operator convenience.
        # Best-effort: a flaky API must never block miner startup; fall back
        # to the `aurelius-deposit` CLI if this banner can't be printed.
        try:
            from aurelius.common.central_api import CentralAPIClient, CentralAPIError

            with CentralAPIClient(self.config.CENTRAL_API_URL, timeout=5) as client:
                addr = client.get_designated_address().address
            if addr:
                logger.info("Work-token deposit address: %s", addr)
                logger.info(
                    "To deposit: btcli stake transfer --origin-netuid %d --dest-netuid %d"
                    " --dest %s --amount <AMOUNT> --network %s",
                    self.config.NETUID,
                    self.config.NETUID,
                    addr,
                    self.config.NETWORK,
                )
        except CentralAPIError as e:
            logger.debug("Could not fetch deposit address banner: %s", e)

    def forward(self, synapse: ScenarioConfigSynapse) -> ScenarioConfigSynapse:
        caller = getattr(getattr(synapse, "dendrite", None), "hotkey", "") or "unknown"
        try:
            caller_uid = self.metagraph.hotkeys.index(caller)
        except ValueError:
            caller_uid = -1

        scenario_config = self.config_store.next()
        if scenario_config is None:
            logger.warning("No configs available to serve")
            return synapse

        result = generate_work_id(scenario_config, self.wallet.hotkey.ss58_address, wallet=self.wallet)

        synapse.scenario_config = scenario_config
        synapse.work_id = result.work_id
        synapse.work_id_nonce = result.nonce
        synapse.work_id_time_ns = result.time_ns
        synapse.work_id_signature = result.signature
        synapse.miner_version = aurelius.__version__
        synapse.miner_protocol_version = PROTOCOL_VERSION

        logger.info(
            "Served ScenarioConfigSynapse | caller_hotkey=%s caller_uid=%s config=%s work_id=%s",
            caller[:16],
            caller_uid,
            scenario_config.get("name", "?"),
            result.work_id[:16],
        )
        return synapse

    def blacklist(self, synapse: ScenarioConfigSynapse) -> Tuple[bool, str]:  # noqa: UP006
        caller = synapse.dendrite.hotkey
        if caller not in self.metagraph.hotkeys:
            reason = f"Hotkey {caller} not in metagraph"
            logger.info("Blacklisted request | caller_hotkey=%s reason=%s", caller[:16], reason)
            return True, reason

        uid = self.metagraph.hotkeys.index(caller)
        # On testnet, validator_permit may not be set for low-stake validators.
        # Allow any registered hotkey to query in testlab mode.
        if not Config.TESTLAB_MODE and not self.metagraph.validator_permit[uid]:
            reason = f"UID {uid} lacks validator permit"
            logger.info("Blacklisted request | caller_hotkey=%s caller_uid=%d reason=%s", caller[:16], uid, reason)
            return True, reason

        logger.debug("Accepted request | caller_hotkey=%s caller_uid=%d", caller[:16], uid)

        return False, ""

    def forward_any(self, synapse: bt.Synapse) -> bt.Synapse:
        """Catch-all for non-ScenarioConfig synapses.

        We do not serve content here; this exists for observability so operators
        can track caller hotkeys and unknown synapse types hitting the axon.
        """
        caller = getattr(getattr(synapse, "dendrite", None), "hotkey", "") or "unknown"
        synapse_type = type(synapse).__name__
        logger.info(
            "Received non-scenario synapse | caller_hotkey=%s synapse_type=%s",
            caller[:16],
            synapse_type,
        )
        return synapse

    def blacklist_any(self, synapse: bt.Synapse) -> Tuple[bool, str]:  # noqa: UP006
        """Blacklist policy for non-ScenarioConfig synapses.

        We log every caller and reject by default to keep miner behavior strict.
        """
        caller = getattr(getattr(synapse, "dendrite", None), "hotkey", "") or "unknown"
        synapse_type = type(synapse).__name__
        uid = -1
        if caller in self.metagraph.hotkeys:
            uid = self.metagraph.hotkeys.index(caller)

        reason = f"Unsupported synapse type: {synapse_type}"
        logger.info(
            "Blacklisted non-scenario synapse | caller_hotkey=%s caller_uid=%s synapse_type=%s reason=%s",
            caller[:16],
            uid,
            synapse_type,
            reason,
        )
        return True, reason

    @staticmethod
    def _detect_external_ip() -> str:
        """Detect external IP using UDP socket trick (no actual traffic sent).

        Falls back to gethostbyname if that fails. Raises RuntimeError if
        all methods return a loopback address.
        """
        # Method 1: UDP connect to public DNS — reveals the default route IP
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if ip and not ip.startswith("127."):
                    return ip
        except OSError:
            pass

        # Method 2: hostname resolution
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if ip and not ip.startswith("127."):
                return ip
        except socket.gaierror:
            pass

        raise RuntimeError(
            "Could not detect a non-loopback external IP. Set AXON_EXTERNAL_IP explicitly in your environment."
        )

    def run(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Miner running. Press Ctrl+C to exit.")
        sync_timeout = max(self.config.METAGRAPH_SYNC_INTERVAL, 60)
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        while not self.should_exit:
            try:
                time.sleep(self.config.METAGRAPH_SYNC_INTERVAL)
                future = executor.submit(self.metagraph.sync, subtensor=self.subtensor)
                try:
                    future.result(timeout=sync_timeout)
                    logger.debug("Metagraph synced: %d neurons", self.metagraph.n)
                except concurrent.futures.TimeoutError:
                    logger.warning("Metagraph sync timed out after %ds — skipping this cycle", sync_timeout)
            except KeyboardInterrupt:
                break
        executor.shutdown(wait=False)

        self.stop()

    def stop(self):
        logger.info("Stopping miner...")
        self.axon.stop()

    def _signal_handler(self, signum, frame):
        logger.info("Received signal %d, shutting down...", signum)
        self.should_exit = True


def _configure_logging():
    log_format = Config.LOG_FORMAT
    if log_format == "json":
        try:
            from pythonjsonlogger import jsonlogger

            handler = logging.StreamHandler()
            handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
            logging.root.handlers = [handler]
            logging.root.setLevel(logging.INFO)
            return
        except ImportError:
            pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def main():
    _configure_logging()
    miner = Miner()
    miner.run()


if __name__ == "__main__":
    main()
