import asyncio
import logging
from datetime import datetime

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
from ocpp.v16 import call_result
from ocpp.v16.enums import Action, RegistrationStatus


logging.basicConfig(level=logging.INFO)


class ChargePoint(cp):
    @on(Action.BootNotification)
    def on_boot_notification(
        self, charge_point_vendor: str, charge_point_model: str, **kwargs
    ):
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status=RegistrationStatus.accepted,
        )

    @on(Action.StartTransaction)
    def on_start_transaction():
        return call_result.StartTransactionPayload(
            transaction_id=10,
            id_tag_info={
                'status': 'Started'
            }
        )

    @on(Action.StopTransaction)
    def on_stop_transaction(self, transaction_id, meter_stop, timestamp, **kwargs):
        # Implement your logic to handle the StopTransaction message here
        # You can access the transaction_id, meter_stop, and timestamp values
        # and perform actions accordingly.

        # For example, you can return a successful response
        return call_result.StopTransactionPayload(
            id_tag_info={
                # 'transactionId': transaction_id,
                'status': 'Accepted',
                'expiryDate': None  # Set expiryDate if needed
            }
        )

    # @on(Action.StatusNotification)
    # def on_status_notification(self, **kwargs):
    #     # Extract the required information from kwargs
    #     connector_id = kwargs.get('connectorId', None)
    #     status = kwargs.get('status', None)
    #     timestamp = kwargs.get('timestamp', None)
    #     error_code = kwargs.get('errorCode', None)

    #     print(connector_id, status, timestamp, error_code)

    @on(Action.Heartbeat)  # Add a Heartbeat message handler
    async def on_heartbeat(self, **kwargs):
        # Send an empty Heartbeat response
        return call_result.HeartbeatPayload(
            current_time=datetime.utcnow().isoformat()
        )

    @on(Action.Authorize)  # Add an Authorize message handler
    async def on_authorize(self, id_tag, **kwargs):
        # Check if the id_tag is valid and authorized
        authorized = self.is_id_tag_authorized(id_tag)

        if authorized:
            return call_result.AuthorizePayload(
                id_tag_info={
                    'status': 'Accepted'
                }
            )
        else:
            return call_result.AuthorizePayload(
                id_tag_info={
                    'status': 'Invalid'
                }
            )

    def is_id_tag_authorized(self, id_tag):
        # Implement your authorization logic here
        # You can check the id_tag against a list of authorized tags
        # Replace with your authorized tags
        authorized_tags = ['1234567890', '0123456789ABCD']
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
