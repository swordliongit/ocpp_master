class OcppRunner:
    async def trigger_remote_start(
        self, charge_point_id, id_token, remote_start_id, target_cps, cmd, evse_id
    ) -> None:
        uri = f"ws://localhost:12315/{charge_point_id}"
        _logger.info("X" * 50 + "\n" + "INSIDE TRIGGER" + "\n" + "X" * 50)
        async with websockets.connect(uri, subprotocols=["ocpp2.0.1"]) as ws:
            # Create a valid OCPP message as a list
            ocpp_message = [
                2,
                "RUNNER",
                "",
                {
                    "idToken": {"idToken": id_token, "type": "Central"},
                    "remoteStartId": remote_start_id,
                    "customData": {'vendorId': "vendor1", 'targetChargePoints': target_cps, 'evseId': evse_id},
                },
            ]

            if cmd == "RequestStartTransaction":
                ocpp_message[2] = "RequestStartTransaction"

            # Send the payload as a JSON string
            await ws.send(json.dumps(ocpp_message))

            # Wait for the response (you may handle the response if needed)
            response = await ws.recv()
            _logger.info("X" * 50 + "\n" + response + "\n" + "X" * 50)


def run_async(self, cp_id, command, evse_id) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    runner = OcppRunner()
    cp_posix = []
    cp_posix.append("CP_RUNNER")  # add the runner to the list so it can receive callbacks
    cp_posix.append(cp_id)
    # _logger.info("X" * 50 + "\n" + str(cp_list) + "\n" + "X" * 50)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        runner.trigger_remote_start(
            charge_point_id="CP_RUNNER",
            id_token="id3123",
            remote_start_id=1,
            target_cps=cp_posix,
            cmd=command,
            evse_id=evse_id,
        )
    )


@api.model
def run_ocpp_middleware(self, cp_id, command, evse_id) -> None:
    # _logger.info("X" * 50 + "\n" + "TEST TEST TEST" + "\n" + "X" * 50)
    t: Thread = Thread(target=self.run_async, args=(cp_id, command, evse_id))
    t.start()
