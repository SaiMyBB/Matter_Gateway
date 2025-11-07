from fastapi import FastAPI, HTTPException
from core.gateway import MatterGateway
from devices.onoff_lamp import OnOffLamp




app = FastAPI(title="Matter Gateway API")

# Initialize gateway and register one device
gateway = MatterGateway()
lamp = OnOffLamp("LivingRoomLamp")
gateway.register_device(lamp)

@app.get("/devices")
def list_devices():
    """List all registered devices and their states"""
    return gateway.get_all_devices()

@app.get("/devices/{name}")
def get_device(name: str):
    device = gateway.get_device(name)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device.read_state()

@app.post("/devices/{name}/{attribute}")
def set_device_state(name: str, attribute: str, value: bool):
    device = gateway.get_device(name)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    success = device.write_state(attribute, value)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid attribute or value")
    return {"message": f"{name} {attribute} updated to {value}"}
