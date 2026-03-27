#!/bin/bash
# Ping the Render app to prevent cold starts (free tier sleeps after 15min idle).
# Schedule via cron every 14 minutes:
#   */14 * * * * /path/to/algo-cus/scripts/keep-alive.sh
curl -sf https://algo-cus.onrender.com/ > /dev/null
