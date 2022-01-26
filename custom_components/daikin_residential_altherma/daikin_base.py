"""Pydaikin base appliance, represent a Daikin device."""

import logging

from .device import DaikinResidentialDevice

from .const import(
    PRESET_BOOST,
    PRESET_TANK_ONOFF,
    PRESET_SETPOINT_MODE,
    ATTR_INSIDE_TEMPERATURE,
    ATTR_OUTSIDE_TEMPERATURE,
    ATTR_ROOM_TEMPERATURE,
    ATTR_TANK_TEMPERATURE,
    ATTR_STATE_OFF,
    ATTR_STATE_ON,
    DAIKIN_CMD_SETS,
    ATTR_ON_OFF_CLIMATE,
    ATTR_ON_OFF_TANK,
    # DAMIANO
    #ATTR_ON_OFF,

    ATTR_OPERATION_MODE,
    ATTR_ENERGY_CONSUMPTION,
    ATTR_ENERGY_CONSUMPTION_TANK,

    SENSOR_PERIOD_WEEKLY,
)

from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_BOOST,
    PRESET_ECO,
    PRESET_NONE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
)

_LOGGER = logging.getLogger(__name__)

HA_PRESET_TO_DAIKIN = {
    PRESET_AWAY: "holidayMode",
    PRESET_NONE: "off",
    PRESET_BOOST: "powerfulMode",
    PRESET_COMFORT: "comfortMode",
    PRESET_ECO: "econoMode",
    PRESET_TANK_ONOFF: "onOffMode",
    PRESET_SETPOINT_MODE: "setpointMode"
}

DAIKIN_HVAC_TO_HA = {
    "dry": HVAC_MODE_DRY,
    "cooling": HVAC_MODE_COOL,
    "heating": HVAC_MODE_HEAT,
    "auto": HVAC_MODE_HEAT_COOL,
    "off": HVAC_MODE_OFF,
}

class Appliance(DaikinResidentialDevice):  # pylint: disable=too-many-public-methods
    """Daikin main appliance class."""

    @staticmethod
    def translate_mac(value):
        """Return translated MAC address."""
        return ":".join(value[i : i + 2] for i in range(0, len(value), 2))

    def __init__(self, jsonData, apiInstance):
        """Init the pydaikin appliance, representing one Daikin device."""
        super().__init__(jsonData, apiInstance)

    async def init(self):
        """Init status."""
        # Re-defined in all sub-classes
        raise NotImplementedError

    def getCommandSet(self, param):
        #print("DAMIANO getCommandSet param = %s",param)

        if param in HA_PRESET_TO_DAIKIN.values():

            def keyByVal(dict,v):
                for k, v in dict.items():
                    if v == param:
                        return v
                    else:
                        continue
                return None
            if keyByVal(HA_PRESET_TO_DAIKIN,"ACS_state") == param:
                cmd_set = DAIKIN_CMD_SETS[ATTR_ON_OFF_TANK].copy()
                cmd_set[1] = param
            else:
                cmd_set = DAIKIN_CMD_SETS[ATTR_PRESET_MODE].copy()
                cmd_set[1] = param
        else:
            cmd_set = DAIKIN_CMD_SETS[param].copy()

        if "%operationMode%" in cmd_set[2]:
            operation_mode = self.getValue(ATTR_OPERATION_MODE)
            cmd_set[2] = cmd_set[2].replace("%operationMode%", operation_mode)
        return cmd_set

    def getData(self, param):
        """Get the current data of a data object."""
        cmd_set = self.getCommandSet(param)
        v = self.get_data(cmd_set[0], cmd_set[1], cmd_set[2])
        return v

    def getDataEC(self, param, mode, period):
        """Get the current data of a data object."""
        if param == "energy_consumption":
            cmd_set = self.getCommandSet(param)
            return self.get_data(cmd_set[0], cmd_set[1], r"{}/{}/{}".format(cmd_set[2],mode,period))
        if param == "energy_consumption_tank":
            cmd_set = self.getCommandSet(param)
            return self.get_data(cmd_set[0], cmd_set[1], r"{}/{}/{}".format(cmd_set[2],mode,period))

        return None


    def getValue(self, param):
        """Get the current value of a data object."""
        data = self.getData(param)
        if data is None:
            return None
        # DAMIANO
        if param == 'holidayMode':
            #print(data)
            return data['/enabled']
        return data["value"]

    def getValidValues(self, param):
        """Get the valid values of a data object."""
        data = self.getData(param)
        if data is None:
            return None
        return data["values"]

    async def setValue(self, param, value):
        """Set the current value of a data object."""
        cmd_set = self.getCommandSet(param)
        return await self.set_data(cmd_set[0], cmd_set[1], cmd_set[2], value)

    @property
    def mac(self):
        """Return device's MAC address."""
        mac_add = self.get_value("gateway", "macAddress")
        if mac_add is None:
            self.get_value("0", "macAddress") # for BigFoot2020
        return mac_add

    @property
    def hvac_mode(self):
        """Return current HVAC mode."""
        mode = HVAC_MODE_OFF
        if self.getValue(ATTR_ON_OFF_CLIMATE) != ATTR_STATE_OFF:
            mode = self.getValue(ATTR_OPERATION_MODE)
        return DAIKIN_HVAC_TO_HA.get(mode, HVAC_MODE_HEAT_COOL)

    @property
    def hvac_modes(self):
        """Return the list of available HVAC modes."""
        modes = [HVAC_MODE_OFF]
        for mode in self.getValidValues(ATTR_OPERATION_MODE):
            modes.append(DAIKIN_HVAC_TO_HA[mode])
        return modes

    async def async_set_hvac_mode(self, hvac_mode):
        """Set HVAC mode."""
        if hvac_mode == HVAC_MODE_OFF:
            return await self.setValue(ATTR_ON_OFF_CLIMATE, ATTR_STATE_OFF)
        else:
            if self.hvac_mode == HVAC_MODE_OFF:
                await self.setValue(ATTR_ON_OFF_CLIMATE, ATTR_STATE_ON)
            return await self.setValue(ATTR_OPERATION_MODE, hvac_mode)

    def support_preset_mode(self, mode):
        """Return True if the device supports preset mode."""
        mode = HA_PRESET_TO_DAIKIN[mode]
        return self.getData(mode) is not None

    def preset_mode_status(self, mode):
        """Return the preset mode status."""
        mode = HA_PRESET_TO_DAIKIN[mode]
        if self.getData(mode) is None:
            return False
        status = self.getValue(mode)
        #print("    DAMIANO Mode {}: {}".format(mode,status))
        return self.getValue(mode)

    async def set_preset_mode_status(self, mode, status):
        """Set the preset mode status."""
        mode = HA_PRESET_TO_DAIKIN[mode]
        if self.getData(mode) is None:
            return
        return await self.setValue(mode, status)

    @property
    def support_tank_temperature(self):
        """Return True if the device supports outsite temperature measurement."""
        return self.getData(ATTR_TANK_TEMPERATURE) is not None

    @property
    def tank_temperature(self):
        """Return tank temperature."""
        fl = float(self.getValue(ATTR_TANK_TEMPERATURE))
        return fl

    @property
    def support_room_temperature(self):
        """Return True if the device supports room temperature measurement."""
        return self.getData(ATTR_ROOM_TEMPERATURE) is not None

    @property
    def room_temperature(self):
        """Return room temperature."""
        fl = float(self.getValue(ATTR_ROOM_TEMPERATURE))
        return fl

    @property
    def support_outside_temperature(self):
        """Return True if the device supports outsite temperature measurement."""
        return self.getData(ATTR_OUTSIDE_TEMPERATURE) is not None

    @property
    def outside_temperature(self):
        """Return current outside temperature."""
        return float(self.getValue(ATTR_OUTSIDE_TEMPERATURE))

    @property
    def inside_temperature(self):
        """Return current inside temperature."""
        #print("DAMIANO ATTR_INSIDE_TEMPERATURE = %s",self.getValue(ATTR_INSIDE_TEMPERATURE))
        return float(self.getValue(ATTR_INSIDE_TEMPERATURE))

    #DAMIANO tutta la proprieta
    @property
    def leaving_water_temperature(self):
        """Return current inside temperature."""
        t = float(self.getValue(ATTR_INSIDE_TEMPERATURE))
        return t

    @property
    def max_temp(self):
        """Return the maximum temperature we are allowed to set."""
        # Only with a separate room temperature we have a
        # max value we can use
        if self._device.support_room_temperature:
            operationMode = self.getValue(ATTR_OPERATION_MODE)
            if operationMode not in ["auto", "cooling", "heating"]:
                return DEFAULT_MAX_TEMP
            return float(self.getData(ATTR_TARGET_ROOM_TEMPERATURE)["maxValue"])
        return DEFAULT_MAX_TEMP

    @property
    def min_temp(self):
        """Return the minimum temperature we are allowed to set."""
        # Only with a separate room temperature we have a
        # min value we can use
        if self._device.support_room_temperature:
            operationMode = self.getValue(ATTR_OPERATION_MODE)
            if operationMode not in ["auto", "cooling", "heating"]:
              return DEFAULT_MIN_TEMP
            return float(self.getData(ATTR_TARGET_ROOM_TEMPERATURE)["minValue"])
        return DEFAULT_MAX_TEMP

    # DAMIANO
    # @property
    # def target_temperature(self):
    #     """Return current target temperature."""
    #     operationMode = self.getValue(ATTR_OPERATION_MODE)
    #     if operationMode not in ["auto", "cooling", "heating"]:
    #         return None
    #     return float(self.getValue(ATTR_TARGET_TEMPERATURE))

    # DAMIANO
    # @property
    # def target_temperature_step(self):
    #     """Return current target temperature."""
    #     operationMode = self.getValue(ATTR_OPERATION_MODE)
    #     if operationMode not in ["auto", "cooling", "heating"]:
    #         return None
    #     return float(self.getData(ATTR_TARGET_TEMPERATURE)["stepValue"])

    async def async_set_temperature(self, value):
        """Set new target temperature."""
        # When we have a separate room temperature we can set the value
        if self._device.support_room_temperature:
            operationMode = self.getValue(ATTR_OPERATION_MODE)
            if operationMode not in ["auto", "cooling", "heating"]:
                return None
            return await self.setValue(ATTR_TARGET_ROOM_TEMPERATURE, value)
        _LOGGER.warning("Set ATTR_TARGET_TEMPERATURE not supported without a separate room temperatur")
        return None

    @property
    def support_energy_consumption(self):
        """Return True if the device supports energy consumption monitoring."""
        #DAMIANO secondo me è un baco
        return self.getData(ATTR_OUTSIDE_TEMPERATURE) is not None
        return True

    def energy_consumption(self, mode, period):
        #DAMIANO
        #def energy_consumption_domestic(self, mode, period):
        """Return the last hour heat power consumption of a given mode in kWh."""
        energy_data = [
            0 if v is None else v

            #damiano
            #for v in self.getData(ATTR_ENERGY_CONSUMPTION)[mode][period]
            # passo anche mode e period
            for v in self.getDataEC(ATTR_ENERGY_CONSUMPTION,mode,period)
        ]
        start_index = 7 if period == SENSOR_PERIOD_WEEKLY else 12
        return sum(energy_data[start_index:])

    # DAMIANO
    def energy_consumption_tank(self, mode, period):
        """Return the last hour heat tank power consumption of a given mode in kWh."""
        energy_data = [
            0 if v is None else v

            #damiano
            #for v in self.getData(ATTR_ENERGY_CONSUMPTION)[mode][period]
            # passo anche mode e period
            for v in self.getDataEC(ATTR_ENERGY_CONSUMPTION_TANK,mode,period)
        ]
        start_index = 7 if period == SENSOR_PERIOD_WEEKLY else 12
        return sum(energy_data[start_index:])

    async def set(self, settings):
        """Set settings on Daikin device."""
        raise NotImplementedError
