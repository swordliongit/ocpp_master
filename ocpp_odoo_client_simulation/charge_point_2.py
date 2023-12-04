try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)


import os
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call, call_result
from ocpp.routing import on

import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)


class ChargePoint(cp):
    async def send_heartbeat(self, interval):
        request = call.HeartbeatPayload()
        while True:
            await self.call(request)
            await asyncio.sleep(interval)

    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charging_station={"model": "Wallbox XYZ", "vendor_name": "anewone"},
            reason="PowerUp",
        )
        response = await self.call(request)

        if response.status == "Accepted":
            print("Connected to central system.")
            await self.send_heartbeat(response.interval)

    @on("RequestStartTransaction")
    async def on_request_start_transaction(self, id_token, remote_start_id):
        print("Received RequestStartTransaction")
        # Add your implementation logic here
        # For example, start a transaction or perform necessary actions
        # You can use the provided id_token and remote_start_id

        # Respond with an accepted status
        return call_result.RequestStartTransactionPayload(status="Accepted")


async def main():
    async with websockets.connect(
        f'ws://{os.getenv("HOST")}:{os.getenv("PORT")}/CP_2', subprotocols=["ocpp2.0.1"]
    ) as ws:
        charge_point = ChargePoint("CP_1", ws)
        await asyncio.gather(charge_point.start(), charge_point.send_boot_notification())


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())
