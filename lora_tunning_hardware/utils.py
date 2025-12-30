from typing import List, Tuple
from .models import Action, State

def format_msg(command: str, params: List[Tuple[str, float]] = []):
  if not params:
    return command
  params_str = ",".join(f"{key}={value}" for key, value in params)
  return f"{command};{params_str}"

def parse_msg(msg: str) -> Tuple[str, List[Tuple[str, float]]]:
  command = None
  params = []
  if ";" in msg:
    command, params_str = msg.split(";", 1)
    params_pairs = []
    if "," in params_str:
      params_pairs = params_str.split(",")
    elif params_str:
      params_pairs = [params_str]

    for param_pair in params_pairs:
      key, val = param_pair.split("=", 1)

      try:
        val_conv = float(val)
      except ValueError:
        val_conv = val

      params.append((key, val_conv))

  return (command, params)

def map_config_to_action(config: List[Tuple[str, float]]) -> Action:
  data = {k.upper(): v for k, v in config}

  return Action(
    FQ=int(data.get("FQ", 0.0)),
    BW=int(data.get("BW", 0.0)),
    SF=int(data.get("SF", 0.0)),
    CR=int(data.get("CR", 0.0)),
    TP=int(data.get("TP", 0.0)),
    IH=int(data.get("IH", 0.0)),
    HS=int(data.get("HS", 0.0)),
    PL=int(data.get("PL", 0.0)),
    CL=int(data.get("CL", 0.0)),
    RT=int(data.get("RT", 0.0))
  )

def map_response_to_state(response: List[Tuple[str, float]]) -> State:
  data = {k.upper(): v for k, v in response}

  return {
    "DELAY": float(data.get("DELAY", 0.0)),
    "RSSI": float(data.get("RSSI", 0.0)),
    "SNR": float(data.get("SNR", 0.0)),
    "TOA": float(data.get("TOA", 0.0)),
    "RTOA": float(data.get("RTOA", 0.0)),
    "BPS": float(data.get("BPS", 0.0)),
    "CHC": float(data.get("CHC", 0.0)),
    "ATT": int(data.get("ATT", 0.0)),
    "ETX": int(data.get("ETX", 0.0))
  }