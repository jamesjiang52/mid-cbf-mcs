# -*- coding: utf-8 -*-
#
# This file is part of the SKA Mid.CBF MCS project
#
# Distributed under the terms of the GPL license.
# See LICENSE for more info.

__all__ = ["SimulatedValues"]

# Simulate some typical values for an idle board
SimulatedValues = {
    "talon_sysid_version": "test",
    "talon_sysid_bitstream": 0xBEEFBABE,
    "talon_status_iopll_locked_fault": False,
    "talon_status_fs_iopll_locked_fault": False,
    "talon_status_comms_iopll_locked_fault": False,
    "talon_status_system_clk_fault": False,
    "talon_status_emif_bl_fault": False,
    "talon_status_emif_br_fault": False,
    "talon_status_emif_tr_fault": False,
    "talon_status_e100g_0_pll_fault": False,
    "talon_status_e100g_1_pll_fault": False,
    "talon_status_slim_pll_fault": False,
    "eth100g_0_counters": [0] * 4,
    "eth100g_0_error_counters": [0] * 6,
    "eth100g_0_data_flow_active": False,
    "eth100g_0_has_data_error": False,
    "eth100g_0_all_tx_counters": [0] * 27,
    "eth100g_0_all_rx_counters": [0] * 27,
    "eth100g_1_counters": [0] * 4,
    "eth100g_1_error_counters": [0] * 6,
    "eth100g_1_data_flow_active": False,
    "eth100g_1_has_data_error": False,
    "eth100g_1_all_tx_counters": [0] * 27,
    "eth100g_1_all_rx_counters": [0] * 27,
    "fpga_die_temperature": 40.0,
    "fpga_die_voltage_0": 12.0,
    "fpga_die_voltage_1": 2.5,
    "fpga_die_voltage_2": 0.8,
    "fpga_die_voltage_3": 1.8,
    "fpga_die_voltage_4": 1.8,
    "fpga_die_voltage_5": 0.9,
    "fpga_die_voltage_6": 1.8,
    "humidity_sensor_temperature": 35.0,
    "dimm_temperatures": [40.0] * 4,
    "mbo_tx_temperatures": [40.0] * 5,
    "mbo_tx_vcc_voltages": [3.3] * 5,
    "mbo_tx_fault_status": [False] * 5,
    "mbo_tx_lol_status": [False] * 5,
    "mbo_tx_los_status": [False] * 5,
    "mbo_rx_vcc_voltages": [3.3] * 5,
    "mbo_rx_lol_status": [False] * 5,
    "mbo_rx_los_status": [False] * 5,
    "has_fan_control": True,
    "fans_pwm": [550] * 4,
    "fans_pwm_enable": [1] * 4,
    "fans_input": [8000] * 4,
    "fans_fault": [False] * 4,
    "ltm_input_voltage": [12.0] * 12,
    "ltm_output_voltage_1": [3.3, 1.0, 0.9, 0.9],
    "ltm_output_voltage_2": [3.3, 1.0, 0.9, 0.9],
    "ltm_input_current": [1.9, 1.9, 0.55, 0.55],
    "ltm_output_current_1": [3.6, 2.5, 3.0, 3.0],
    "ltm_output_current_2": [3.6, 2.5, 3.0, 3.0],
    "ltm_temperature_1": [50.0] * 12,
    "ltm_temperature_2": [50.0] * 12,
    "ltm_voltage_warning": [False] * 12,
    "ltm_current_warning": [False] * 12,
    "ltm_temperature_warning": [False] * 12,
}
