module.exports = {
  apps: [
    {
      name: "aurelius-miner",
      cwd: __dirname,
      script: "./scripts/start-miner.sh",
      interpreter: "none",
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 20,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
