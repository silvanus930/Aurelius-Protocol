module.exports = {
  apps: [
    {
      name: "aurelius-miner-1",
      cwd: __dirname,
      script: "./scripts/start-miner.sh",
      interpreter: "none",
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 20,
      env: {
        ENV_FILE: "/root/Aurelius-Protocol/.env.miner1",
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "aurelius-miner-2",
      cwd: __dirname,
      script: "./scripts/start-miner.sh",
      interpreter: "none",
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 20,
      env: {
        ENV_FILE: "/root/Aurelius-Protocol/.env.miner2",
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "aurelius-miner-3",
      cwd: __dirname, 
      script: "./scripts/start-miner.sh",
      interpreter: "none",
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 20,
      env: {
        ENV_FILE: "/root/Aurelius-Protocol/.env.miner3",
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
