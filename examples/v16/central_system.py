import asyncio
import logging
from datetime import datetime
import threading

from ocpp.v16 import enums

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)

from ocpp.routing import on
from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call_result, call
from ocpp.v16.enums import Action, RegistrationStatus, RemoteStartStopStatus


logging.basicConfig(level=logging.INFO)


class ChargePoint(cp):
    @on(Action.BootNotification)
    async def on_boot_notification(
        self, charge_point_vendor: str, charge_point_model: str, **kwargs
    ):
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status=RegistrationStatus.accepted,
        )

    async def schedule_RemoteStartTransaction(self):
        await asyncio.sleep(5)  # Wait for 10 seconds
        # await self.prompt_caller()  # Call the prompt_caller function after 10 seconds
        await self.on_remote_start(id_tag="0123456789ABCD", connector_id=1)

    @on(Action.StartTransaction)
    def on_start_transaction(self, **kwargs):
        return call_result.StartTransactionPayload(
            transaction_id=10, id_tag_info={"status": "Accepted"}
        )

    @on(Action.StopTransaction)
    def on_stop_transaction(self, meter_stop, timestamp, transaction_id):
        print("meterStop", meter_stop)
        print("timestamp", timestamp)
        print("transactionId", transaction_id)
        return call_result.StopTransactionPayload(id_tag_info={"status": "Accepted"})

    @on(Action.RemoteStartTransaction)
    async def on_remote_start(self, id_tag, connector_id):
        print("remotely starting")
        print("idTag:", id_tag)
        print("connectorId:", connector_id)
        return await self.remote_start_transaction(id_tag, connector_id)

    async def remote_start_transaction(self, id_tag, connector_id):
        obj = {
            "chargingProfileId": 1,
            "stackLevel": 0,
            "chargingProfilePurpose": enums.ChargingProfilePurposeType.chargepointmaxprofile,
            "chargingProfileKind": enums.ChargingProfileKindType.absolute,
            "chargingSchedule": {
                "startSchedule": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") + "Z",
                "chargingRateUnit": enums.ChargingRateUnitType.amps,
                "chargingSchedulePeriod": [{"startPeriod": 0, "limit": 8.0}],
            },
        }
        print("REMOTE START!!!")
        request = call.RemoteStartTransactionPayload(
            id_tag=id_tag, connector_id=connector_id
        )
        response = await self.call(request)
        # print(response)
        if response.status == RemoteStartStopStatus.accepted:
            print("Transaction Started!!!")
        else:
            print("Transaction Failed to Start!!!")
            # print(response.status)
            # websockets.send("Transaction Started!!!")

    # async def prompt_caller(self):
    #     self.start_remote_transaction = False
    #     threading.Thread(target=self.prompt_for_remote).start()
    #     while not self.start_remote_transaction:
    #         await asyncio.sleep(1)
    #     if self.start_remote_transaction:
    #         await self.on_remote_start(id_tag="0123456789ABCD", connector_id=1)

    # def prompt_for_remote(self):
    #     input_text = input("Press Enter to authorize: ")
    #     if input_text.strip() == "":
    #         self.start_remote_transaction = True

    # async def remote_stop_transaction(self, transaction_id):
    #     print("REMOTE STOP!!!")
    #     request = call.RemoteStopTransactionPayload(transaction_id=transaction_id)
    #     response = await self.call(request)

    #     if response.status == RemoteStartStopStatus.accepted:
    #         print("Stopping transaction")
    #     # websockets.send("Transaction Stopped!!!")

    #     @on(Action.StopTransaction)
    #     def on_stop_transaction(self, transaction_id, meter_stop, timestamp, **kwargs):
    #         # Implement your logic to handle the StopTransaction message here
    #         # You can access the transaction_id, meter_stop, and timestamp values
    #         # and perform actions accordingly.

    #         # For example, you can return a successful response
    #         return call_result.StopTransactionPayload(
    #             id_tag_info={
    #                 # 'transactionId': transaction_id,
    #                 "status": "Accepted",
    #                 "expiryDate": None,  # Set expiryDate if needed
    #             }
    #         )

    @on(Action.MeterValues)
    async def on_meter_values(self, connector_id, transaction_id, meter_value):
        # Handle the MeterValues message here
        print("Received MeterValues:")
        print(f"Connector ID: {connector_id}")
        print(f"Transaction ID: {transaction_id}")
        print(f"Meter Value: {meter_value}")

        # Implement your logic for handling meter values here

        # Respond to the MeterValues message with a confirmation if needed
        return call_result.MeterValuesPayload()

    @on(Action.StatusNotification)
    async def on_status_notification(self, connector_id, error_code, status, timestamp):
        # Handle the StatusNotification message here
        print("Received StatusNotification:")
        print(f"Connector ID: {connector_id}")
        print(f"Error Code: {error_code}")
        print(f"Status: {status}")
        print(f"Timestamp: {timestamp}")

        if status == "Preparing":
            # Schedule the prompt_caller function to be called after 10 seconds
            loop = asyncio.get_event_loop()
            loop.create_task(self.schedule_RemoteStartTransaction())

        # You can implement your logic for handling the status change

        # Respond to the StatusNotification with a confirmation if needed
        return call_result.StatusNotificationPayload()

    @on(Action.Heartbeat)  # Add a Heartbeat message handler
    async def on_heartbeat(self, **kwargs):
        # Send an empty Heartbeat response
        return call_result.HeartbeatPayload(current_time=datetime.utcnow().isoformat())

    @on(Action.Authorize)
    async def on_authorize(self, id_tag, **kwargs):
        if self.is_id_tag_authorized(id_tag):
            return call_result.AuthorizePayload(id_tag_info={"status": "Accepted"})
        else:
            return call_result.AuthorizePayload(id_tag_info={"status": "Invalid"})

    def is_id_tag_authorized(self, id_tag):
        # Implement your authorization logic here
        # You can check the id_tag against a list of authorized tags
        # Replace with your authorized tags
        authorized_tags = ["1234567890", "0123456789ABCD"]
        return id_tag in authorized_tags


async def on_connect(websocket, path):
    """For every new charge point that connects, create a ChargePoint
    instance and start listening for messages.
    """
    try:
        requested_protocols = websocket.request_headers["Sec-WebSocket-Protocol"]
    except KeyError:
        logging.error("Client hasn't requested any Subprotocol. Closing Connection")
        return await websocket.close()
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s", websocket.subprotocol)
    else:
        # In the websockets lib if no subprotocols are supported by the
        # client and the server, it proceeds without a subprotocol,
        # so we have to manually close the connection.
        logging.warning(
            "Protocols Mismatched | Expected Subprotocols: %s,"
            " but client supports  %s | Closing connection",
            websocket.available_subprotocols,
            requested_protocols,
        )
        return await websocket.close()

    charge_point_id = path.strip("/")
    cp = ChargePoint(charge_point_id, websocket)

    await cp.start()


async def main():
    server = await websockets.serve(
        on_connect, "192.168.100.44", 9000, subprotocols=["ocpp1.6"]
    )

    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())
