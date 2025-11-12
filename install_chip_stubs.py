#!/usr/bin/env python3
"""
FINAL PATCH + FilterType support
Fully resolves all chip.discovery imports used by matter_server.
"""

import sys, os, types

site_path = next(p for p in sys.path if p.endswith("site-packages"))
target_dir = os.path.join(site_path, "chip")
os.makedirs(target_dir, exist_ok=True)
stub_path = os.path.join(target_dir, "__init__.py")

print(f"🧩 Installing FINAL CHIP stub (FilterType added) at {stub_path}")

content = r'''
import sys, types

chip = sys.modules[__name__]

# ------------------------------
# Utility
# ------------------------------
class ChipUtility:
    @staticmethod
    def IsNull(v): return v is None
    @staticmethod
    def ConvertToHex(d): return "00" * len(str(d))
    @staticmethod
    def classproperty(func):
        """Decorator to emulate CHIP SDK @classproperty."""
        class _ClassProperty:
            def __get__(self, obj, cls): return func(cls)
        return _ClassProperty()

chip.ChipUtility = ChipUtility
sys.modules["chip.ChipUtility"] = chip

# ------------------------------
# clusters
# ------------------------------
clusters = types.ModuleType("chip.clusters")

Attribute = types.ModuleType("chip.clusters.Attribute")
class AttributeWriteResult: ...
class ValueDecodeFailure(Exception): ...
Attribute.AttributeWriteResult = AttributeWriteResult
Attribute.ValueDecodeFailure = ValueDecodeFailure
sys.modules["chip.clusters.Attribute"] = Attribute

Types = types.SimpleNamespace(Nullable=None, NullValue=None)
sys.modules["chip.clusters.Types"] = Types

ClusterObjects = types.ModuleType("chip.clusters.ClusterObjects")
class Cluster: pass
class ClusterAttributeDescriptor: pass
class ClusterObjectDescriptor: pass
class ClusterObjectFieldDescriptor: pass
class ClusterCommand: pass
class ClusterObjectField: pass
ClusterObjects.ALL_ATTRIBUTES = {}
ClusterObjects.ALL_CLUSTERS = {}
ClusterObjects.Cluster = Cluster
ClusterObjects.ClusterAttributeDescriptor = ClusterAttributeDescriptor
ClusterObjects.ClusterObjectDescriptor = ClusterObjectDescriptor
ClusterObjects.ClusterObjectFieldDescriptor = ClusterObjectFieldDescriptor
ClusterObjects.ClusterCommand = ClusterCommand
ClusterObjects.ClusterObjectField = ClusterObjectField
sys.modules["chip.clusters.ClusterObjects"] = ClusterObjects

Objects = types.ModuleType("chip.clusters.Objects")
class _BaseCluster: 
    def __repr__(self): return f"<Cluster {self.__class__.__name__}>"

for cname in [
    "BasicInformation","ElectricalPowerMeasurement","OnOff",
    "LevelControl","Thermostat","TemperatureMeasurement",
    "RelativeHumidityMeasurement","IlluminanceMeasurement",
    "LeakDetection","PowerConfiguration","EnergyMeasurement",
    "Identify"
]:
    setattr(Objects, cname, type(cname, (_BaseCluster,), {}))
Objects.ALL = {n: getattr(Objects, n) for n in dir(Objects) if not n.startswith("_")}
sys.modules["chip.clusters.Objects"] = Objects

clusters.Attribute = Attribute
clusters.Types = Types
clusters.Objects = Objects
clusters.ClusterObjects = ClusterObjects
sys.modules["chip.clusters"] = clusters

# ------------------------------
# discovery (patched)
# ------------------------------
discovery = types.ModuleType("chip.discovery")

class DiscoveryType:
    DNS = 1
    MDNS = 2

class FilterType:
    """Used by OTA and controller discovery."""
    NONE = 0
    SHORT_DISCOVERY = 1
    LONG_DISCOVERY = 2
    BY_INSTANCE_NAME = 3
    BY_COMMISSIONER_NAME = 4

discovery.DiscoveryType = DiscoveryType
discovery.FilterType = FilterType
sys.modules["chip.discovery"] = discovery

# ------------------------------
# remaining
# ------------------------------
ChipDeviceCtrl = types.ModuleType("chip.ChipDeviceCtrl")
ChipDeviceCtrl.ChipDeviceController = object
sys.modules["chip.ChipDeviceCtrl"] = ChipDeviceCtrl

exceptions = types.ModuleType("chip.exceptions")
exceptions.ChipStackError = Exception
sys.modules["chip.exceptions"] = exceptions

tlv = types.ModuleType("chip.tlv")
tlv.float32 = float; tlv.uint = int
sys.modules["chip.tlv"] = tlv

native = types.ModuleType("chip.native")
class PyChipError(Exception): ...
native.PyChipError = PyChipError
sys.modules["chip.native"] = native

for n in ["chip.logging", "chip.controller", "chip.commissionable", "chip.cluster"]:
    sys.modules[n] = types.ModuleType(n)

print("⚙️ Using FINAL CHIP stubs (FilterType included).")
'''

with open(stub_path, "w") as f:
    f.write(content.strip() + "\n")

print("✅ Installed FINAL CHIP stubs with FilterType.")
print("Now run: python3 matter_bridge.py")
