import logging
import serial.tools.list_ports
import threading
import asyncio
from typing import Dict
from .models import Action, State
from .utils import format_msg, parse_msg, map_config_to_action, map_response_to_state

class LoraHardware():
  def __init__(self, logger: logging.Logger, port_filter: str = ""):
    self.port_filter = port_filter
    self.logger = logger
    self.ser = None
    self.thread = None
    self.running = False
    self.pending_futures: Dict[str, asyncio.Future] = {}
    self.loop: threading.AbstractEventLoop = None
    self.sent_history: list[str] = []

  async def start(self):
    self.loop = asyncio.get_running_loop()
    self.serial_port = self.find_serial_port(self.port_filter)
    self.start_listener()

  async def stop(self):
    self.stop_listener()

  def find_serial_port(self, filter: str) -> str:
    ports = serial.tools.list_ports.comports()
    for port in ports:
      if port.device.startswith(filter):
        return port.device
    return None
  
  def start_listener(self):
    self.ser = serial.Serial(port=self.serial_port, baudrate=115200, timeout=1)
    self.running = True
    self.thread = threading.Thread(target=self.read_serial, daemon=True)
    self.thread.start()
    self.logger.info(f"Listening thread started on {self.serial_port}")

  def stop_listener(self):
    self.running = False
    if self.thread and self.thread.is_alive():
      self.thread.join(timeout=2)
    self.logger.info("Listener stopped")

  def read_serial(self):
    self.logger.info(f"Connected to {self.serial_port}")

    try:
      while True:
        if self.ser.in_waiting > 0:
          line = self.ser.readline().decode("utf-8", errors="ignore").strip()
          if line:
            self.logger.info(line)
            self.serial_handler(line)
    except Exception as e:
      self.logger.error(f"Error in read_serial: {e}")
    finally:
      self.ser.close()
      self.logger.info("Serial connection closed")

    self.running = False
    if self.thread and self.thread.is_alive():
      self.thread.join(timeout=2)
    self.logger.info("Listener stopped")

  def write_serial(self, data: str) -> None: 
    if self.ser and self.ser.is_open:
      try:
        self.ser.write((data + "\r\n").encode("utf-8"))
        self.sent_history.append(data)
      except Exception as e:
        self.logger.error(f"Error writing to serial: {e}")
    else:
      self.logger.warning("Serial port is not open")

  async def config_get(self) -> Action:
    future = self.loop.create_future()
    self.pending_futures["CONFIG_GET"] = future
    msg = format_msg("CONFIG_GET")
    self.write_serial(msg)
    action = await future
    return action
  
  async def ping(self, id: int) -> State:
    future = self.loop.create_future()
    self.pending_futures['PING'] = future
    msg = format_msg("PING", [("ID", id)])
    self.write_serial(msg)
    state = await future
    return state
  
  async def config_sync(self, id: int, params: Action) -> bool:
    configs = list(params.items())
    future = self.loop.create_future()
    self.pending_futures['CONFIG_SYNC'] = future
    msg = format_msg("CONFIG_SYNC", [("ID", id), *configs])
    self.write_serial(msg)
    result = await future
    return result
  
  def serial_handler(self, msg: str):
    command, params = parse_msg(msg)
    if command:
      match command:
        case "CONFIG_GET":
          future = self.pending_futures.pop("CONFIG_GET", None)
          if future and not future.done():
             parsed_params = map_config_to_action(params)
             self.loop.call_soon_threadsafe(future.set_result, parsed_params)
        case "PING_ACK":
          future = self.pending_futures.pop("PING", None)
          if future and not future.done():
            parsed_params = map_response_to_state(params)
            self.loop.call_soon_threadsafe(future.set_result, parsed_params)
        case "PING_NO_ACK":
          future = self.pending_futures.pop("PING", None)
          if future and not future.done():
            self.loop.call_soon_threadsafe(future.set_result, None)
        case "CONFIG_SYNC_CHECK_ACK":
          future = self.pending_futures.pop("CONFIG_SYNC", None)
          if future and not future.done():
            parsed_params = map_response_to_state(params)
            self.loop.call_soon_threadsafe(future.set_result, True)
        case "CONFIG_SYNC_CHECK_NO_ACK":
          future = self.pending_futures.pop("CONFIG_SYNC", None)
          if future and not future.done():
            self.loop.call_soon_threadsafe(future.set_result, False)
        case "CONFIG_SYNC_NO_ACK":
          future = self.pending_futures.pop("CONFIG_SYNC", None)
          if future and not future.done():
            self.logger.info(f'Cannot sync CONFIG_SYNC_NO_ACK last action: {self.sent_history[-1]}')
            self.loop.call_soon_threadsafe(future.set_result, False)
        case "CONFIG_SYNC_ACK_NO_ACK":
          future = self.pending_futures.pop("CONFIG_SYNC", None)
          if future and not future.done():
            self.logger.info(f'Cannot sync CONFIG_SYNC_ACK_NO_ACK last action: {self.sent_history[-1]}')
            self.loop.call_soon_threadsafe(future.set_result, None)
        case _:
          self.logger.warning(f"Unknown command {command}")
