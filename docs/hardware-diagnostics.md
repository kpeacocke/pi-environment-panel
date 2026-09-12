# Live hardware diagnosis — 12–13 September 2026

## Working display confirmed — 13 September, 08:43 AEST

A read-only SSH capture confirmed the user's report of live display updates.
The running 0.1.6 service uses `/dev/ttyAMA10` at 115200, WAKE GPIO22 and
RESET GPIO17. Its journal records successful command sends at 08:35:54 and
08:42:53. A failed handshake at 08:41:51 recovered on the next attempt.
`display-status.json` reports `handshake_ok: true` for the 08:42:47 sample.
UART10 counters were TX 1457, RX 124; the boot began around 08:35.
No service restart, serial probe, GPIO change or reboot was performed during
this capture. Software handshake/send evidence and the user's visible updates
establish a working display path. They do not establish why earlier attempts
failed or prove a cable fault.

The GPS collector still reports `GPS waiting for fix`; local weather consequently
remains unavailable. The modem uses the separate `/dev/ttyAMA0` port. This is
independent of the now-confirmed working display connection.

The failure observations below are historical, not the current display state.

## Confirmed software and port separation

The installed service runs pi-environment-panel 0.1.6 from its own venv, with
`/etc/pi-environment-panel/config.toml`. E-paper uses `/dev/ttyAMA10`, 115200,
WAKE GPIO22 and RESET GPIO17. SIM7600NA-H GNSS uses `/dev/ttyAMA0`, 115200.
The modem answers AT commands. No competing serial client was running during
isolated tests. The Pi reported `throttled=0x0`; that does not measure voltage
at either peripheral's power terminals.

## GPS: no fix originates in the receiver

The receiver returned:

```text
AT+CGPS?        -> +CGPS: 1,1
AT+CGPSINFO     -> +CGPSINFO: ,,,,,,,,
AT+CGNSSINFO    -> +CGNSSINFO: ,,,,,,,,,,,,,,,
AT+CGNSSMODE?   -> +CGNSSMODE: 3,2
AT+CGPSNMEA?    -> +CGPSNMEA: 198143
```

Temporarily enabling `AT+CGPSINFOCFG=1,77` produced these raw NMEA sentences:

```text
$GPGGA,,,,,,0,,,,,,,,*66
$GPGSA,A,1,,,,,,,,,,,,,,,*1E
```

GGA reports invalid fix quality (0); GSA reports no fix (1) and no satellite IDs
used. No GSV sentence was captured in the sample. This does **not** prove that
zero satellites are physically visible: it establishes that the receiver supplied
no satellite observations in these reports. Weather parsing cannot manufacture a
valid position from them.

A clean GNSS cold start was performed: `AT+CGPS=0`, wait one second, then
`AT+CGPSCOLD`. Both returned OK; the receiver returned to `+CGPS: 1,1`.
An immediate cold-start command without the stop-settle delay was rejected.
A subsequent 30-second NMEA capture still returned the same no-fix sentences.
Periodic NMEA reporting was restored to its original `AT+CGPSINFOCFG=0,0` setting.
GNSS was left enabled, and the service resumed normal polling.

The supplied photographs show the e-paper connector and Pi UART cable, but do not
show readable GNSS antenna connector labels or establish antenna continuity,
antenna supply voltage, or received RF signal strength. Those remain unverified.
The remaining GNSS investigation is reception/antenna hardware or receiver
behaviour, not a missing weather-coordinate conversion. No constellation or
assisted-GPS settings were changed speculatively.

## Display: failure reproduced immediately after reboot

Direct known Waveshare handshake requests at 115200 returned no data. Holding
RESET inactive high and waking through GPIO22 did not produce a response in the
previous controlled check. The service's failed handshake prevents drawing, as
intended; `latest.json` is sensor sampling and is not proof of a screen update.

The user reported an earlier visible dashboard after restarting. To test whether
reboot reliably recovers it, a controlled Pi reboot was performed at about 22:54
AEST. The first post-boot service update logged `e-paper handshake failed`.
The kernel UART10 counters were TX 18, RX 0. Thus no successful exchange was
observed after this reboot either. Before reboot, UART10 had accumulated 30 RX
bytes over many failed attempts, but their content was not captured; they cannot
be called valid acknowledgements.

This rules out treating reboot as a verified lasting fix. It does not establish
which conductor or component is faulty. The dedicated UART path and runtime
settings are confirmed; the cause remained unresolved at that time. Later successful exchanges are
recorded above; they do not justify attributing the earlier failures to wiring.
Do not rewire based solely on adapter wire colours or an obscured photograph.

Both the dashboard service and GPS polling were restored after testing. Existing
software and the GPS-to-weather integration remain published on GitHub. Runtime
coordinates and private keys are excluded from the repository.

## References

- [SIMCom GNSS application note](https://files.waveshare.com/upload/e/e1/SIM7500_SIM7600_Series_GNSS_Application_Note_V2.00.pdf)
- [SIMCom AT command manual](https://files.waveshare.com/wiki/CM5-DUAL-ETH-BASE/SIM7500_SIM7600_Series_AT_Command_Manual_V2.00.pdf)
- [Waveshare UART e-paper](https://www.waveshare.com/wiki/4.3inch_e-Paper_UART_Module)
- [Pi debug connector pinout](https://datasheets.raspberrypi.com/debug/debug-connector-specification.pdf)
