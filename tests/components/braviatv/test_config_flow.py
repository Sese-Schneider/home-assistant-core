"""Define tests for the Bravia TV config flow."""
from unittest.mock import patch

from pybravia import (
    BraviaTVAuthError,
    BraviaTVConnectionError,
    BraviaTVError,
    BraviaTVNotSupported,
)
import pytest

from homeassistant import data_entry_flow
from homeassistant.components import ssdp
from homeassistant.components.braviatv.const import (
    CONF_CLIENT_ID,
    CONF_IGNORED_SOURCES,
    CONF_NICKNAME,
    CONF_USE_PSK,
    DOMAIN,
    NICKNAME_PREFIX,
)
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_SSDP, SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_PIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import instance_id

from tests.common import MockConfigEntry

BRAVIA_SYSTEM_INFO = {
    "product": "TV",
    "region": "XEU",
    "language": "pol",
    "model": "TV-Model",
    "serial": "serial_number",
    "macAddr": "AA:BB:CC:DD:EE:FF",
    "name": "BRAVIA",
    "generation": "5.2.0",
    "area": "POL",
    "cid": "very_unique_string",
}

BRAVIA_SOURCES = [
    {"title": "HDMI 1", "uri": "extInput:hdmi?port=1"},
    {"title": "HDMI 2", "uri": "extInput:hdmi?port=2"},
    {"title": "HDMI 3/ARC", "uri": "extInput:hdmi?port=3"},
    {"title": "HDMI 4", "uri": "extInput:hdmi?port=4"},
    {"title": "AV/Component", "uri": "extInput:component?port=1"},
]

BRAVIA_SSDP = ssdp.SsdpServiceInfo(
    ssdp_usn="mock_usn",
    ssdp_st="mock_st",
    ssdp_location="http://bravia-host:52323/dmr.xml",
    upnp={
        ssdp.ATTR_UPNP_UDN: "uuid:1234",
        ssdp.ATTR_UPNP_FRIENDLY_NAME: "Living TV",
        ssdp.ATTR_UPNP_MODEL_NAME: "KE-55XH9096",
        "X_ScalarWebAPI_DeviceInfo": {
            "X_ScalarWebAPI_ServiceList": {
                "X_ScalarWebAPI_ServiceType": [
                    "guide",
                    "system",
                    "audio",
                    "avContent",
                    "videoScreen",
                ],
            },
        },
    },
)

FAKE_BRAVIA_SSDP = ssdp.SsdpServiceInfo(
    ssdp_usn="mock_usn",
    ssdp_st="mock_st",
    ssdp_location="http://soundbar-host:52323/dmr.xml",
    upnp={
        ssdp.ATTR_UPNP_UDN: "uuid:1234",
        ssdp.ATTR_UPNP_FRIENDLY_NAME: "Sony Audio Device",
        ssdp.ATTR_UPNP_MODEL_NAME: "HT-S700RF",
        "X_ScalarWebAPI_DeviceInfo": {
            "X_ScalarWebAPI_ServiceList": {
                "X_ScalarWebAPI_ServiceType": ["guide", "system", "audio", "avContent"],
            },
        },
    },
)


async def test_show_form(hass):
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER


async def test_ssdp_discovery(hass):
    """Test that the device is discovered."""
    uuid = await instance_id.async_get(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data=BRAVIA_SSDP,
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "confirm"

    with patch("pybravia.BraviaTV.connect"), patch("pybravia.BraviaTV.pair"), patch(
        "pybravia.BraviaTV.set_wol_mode"
    ), patch(
        "pybravia.BraviaTV.get_system_info",
        return_value=BRAVIA_SYSTEM_INFO,
    ), patch(
        "homeassistant.components.braviatv.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        await hass.async_block_till_done()

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "authorize"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_USE_PSK: False}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "pin"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PIN: "1234"}
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["result"].unique_id == "very_unique_string"
        assert result["title"] == "TV-Model"
        assert result["data"] == {
            CONF_HOST: "bravia-host",
            CONF_PIN: "1234",
            CONF_USE_PSK: False,
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
            CONF_CLIENT_ID: uuid,
            CONF_NICKNAME: f"{NICKNAME_PREFIX} {uuid[:6]}",
        }


async def test_ssdp_discovery_fake(hass):
    """Test that not Bravia device is not discovered."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data=FAKE_BRAVIA_SSDP,
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "not_bravia_device"


async def test_ssdp_discovery_exist(hass):
    """Test that the existed device is not discovered."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="very_unique_string",
        data={
            CONF_HOST: "bravia-host",
            CONF_PIN: "1234",
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
        },
        title="TV-Model",
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_SSDP},
        data=BRAVIA_SSDP,
    )

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_invalid_host(hass):
    """Test that errors are shown when the host is invalid."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: "invalid/host"}
    )

    assert result["errors"] == {CONF_HOST: "invalid_host"}


@pytest.mark.parametrize(
    "side_effect, error_message",
    [
        (BraviaTVAuthError, "invalid_auth"),
        (BraviaTVNotSupported, "unsupported_model"),
        (BraviaTVConnectionError, "cannot_connect"),
    ],
)
async def test_pin_form_error(hass, side_effect, error_message):
    """Test that PIN form errors are correct."""
    with patch(
        "pybravia.BraviaTV.connect",
        side_effect=side_effect,
    ), patch("pybravia.BraviaTV.pair"):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: "bravia-host"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_USE_PSK: False}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PIN: "1234"}
        )

        assert result["errors"] == {"base": error_message}


@pytest.mark.parametrize(
    "side_effect, error_message",
    [
        (BraviaTVAuthError, "invalid_auth"),
        (BraviaTVNotSupported, "unsupported_model"),
        (BraviaTVConnectionError, "cannot_connect"),
    ],
)
async def test_psk_form_error(hass, side_effect, error_message):
    """Test that PSK form errors are correct."""
    with patch(
        "pybravia.BraviaTV.connect",
        side_effect=side_effect,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: "bravia-host"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_USE_PSK: True}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PIN: "mypsk"}
        )

        assert result["errors"] == {"base": error_message}


async def test_no_ip_control(hass):
    """Test that error are shown when IP Control is disabled on the TV."""
    with patch("pybravia.BraviaTV.pair", side_effect=BraviaTVError):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: "bravia-host"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_USE_PSK: False}
        )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "no_ip_control"


async def test_duplicate_error(hass):
    """Test that error are shown when duplicates are added."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="very_unique_string",
        data={
            CONF_HOST: "bravia-host",
            CONF_PIN: "1234",
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
        },
        title="TV-Model",
    )
    config_entry.add_to_hass(hass)

    with patch("pybravia.BraviaTV.connect"), patch("pybravia.BraviaTV.pair"), patch(
        "pybravia.BraviaTV.set_wol_mode"
    ), patch(
        "pybravia.BraviaTV.get_system_info",
        return_value=BRAVIA_SYSTEM_INFO,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: "bravia-host"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_USE_PSK: False}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PIN: "1234"}
        )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_create_entry(hass):
    """Test that entry is added correctly with PIN auth."""
    uuid = await instance_id.async_get(hass)

    with patch("pybravia.BraviaTV.connect"), patch("pybravia.BraviaTV.pair"), patch(
        "pybravia.BraviaTV.set_wol_mode"
    ), patch(
        "pybravia.BraviaTV.get_system_info",
        return_value=BRAVIA_SYSTEM_INFO,
    ), patch(
        "homeassistant.components.braviatv.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: "bravia-host"}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "authorize"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_USE_PSK: False}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "pin"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PIN: "1234"}
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["result"].unique_id == "very_unique_string"
        assert result["title"] == "TV-Model"
        assert result["data"] == {
            CONF_HOST: "bravia-host",
            CONF_PIN: "1234",
            CONF_USE_PSK: False,
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
            CONF_CLIENT_ID: uuid,
            CONF_NICKNAME: f"{NICKNAME_PREFIX} {uuid[:6]}",
        }


async def test_create_entry_psk(hass):
    """Test that entry is added correctly with PSK auth."""
    with patch("pybravia.BraviaTV.connect"), patch(
        "pybravia.BraviaTV.set_wol_mode"
    ), patch(
        "pybravia.BraviaTV.get_system_info",
        return_value=BRAVIA_SYSTEM_INFO,
    ), patch(
        "homeassistant.components.braviatv.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: "bravia-host"}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "authorize"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_USE_PSK: True}
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "psk"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PIN: "mypsk"}
        )

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["result"].unique_id == "very_unique_string"
        assert result["title"] == "TV-Model"
        assert result["data"] == {
            CONF_HOST: "bravia-host",
            CONF_PIN: "mypsk",
            CONF_USE_PSK: True,
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
        }


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="very_unique_string",
        data={
            CONF_HOST: "bravia-host",
            CONF_PIN: "1234",
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
        },
        title="TV-Model",
    )
    config_entry.add_to_hass(hass)

    with patch("pybravia.BraviaTV.connect"), patch(
        "pybravia.BraviaTV.get_power_status",
        return_value="active",
    ), patch(
        "pybravia.BraviaTV.get_external_status",
        return_value=BRAVIA_SOURCES,
    ), patch(
        "pybravia.BraviaTV.send_rest_req",
        return_value={},
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.options.async_init(config_entry.entry_id)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={CONF_IGNORED_SOURCES: ["HDMI 1", "HDMI 2"]}
        )
        await hass.async_block_till_done()

        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert config_entry.options == {CONF_IGNORED_SOURCES: ["HDMI 1", "HDMI 2"]}

        # Test that saving with missing sources is ok
        with patch(
            "pybravia.BraviaTV.get_external_status",
            return_value=BRAVIA_SOURCES[1:],
        ):
            result = await hass.config_entries.options.async_init(config_entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], user_input={CONF_IGNORED_SOURCES: ["HDMI 1"]}
            )
            await hass.async_block_till_done()
            assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
            assert config_entry.options == {CONF_IGNORED_SOURCES: ["HDMI 1"]}


async def test_options_flow_error(hass: HomeAssistant) -> None:
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="very_unique_string",
        data={
            CONF_HOST: "bravia-host",
            CONF_PIN: "1234",
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
        },
        title="TV-Model",
    )
    config_entry.add_to_hass(hass)

    with patch("pybravia.BraviaTV.connect"), patch(
        "pybravia.BraviaTV.get_power_status",
        return_value="active",
    ), patch(
        "pybravia.BraviaTV.get_external_status",
        return_value=BRAVIA_SOURCES,
    ), patch(
        "pybravia.BraviaTV.send_rest_req",
        return_value={},
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    with patch(
        "pybravia.BraviaTV.send_rest_req",
        side_effect=BraviaTVError,
    ):
        result = await hass.config_entries.options.async_init(config_entry.entry_id)

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "failed_update"


@pytest.mark.parametrize(
    "use_psk, new_pin",
    [
        (True, "7777"),
        (False, "newpsk"),
    ],
)
async def test_reauth_successful(hass, use_psk, new_pin):
    """Test that the reauthorization is successful."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="very_unique_string",
        data={
            CONF_HOST: "bravia-host",
            CONF_PIN: "1234",
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
        },
        title="TV-Model",
    )
    config_entry.add_to_hass(hass)

    with patch("pybravia.BraviaTV.connect"), patch(
        "pybravia.BraviaTV.get_power_status",
        return_value="active",
    ), patch(
        "pybravia.BraviaTV.get_external_status",
        return_value=BRAVIA_SOURCES,
    ), patch(
        "pybravia.BraviaTV.send_rest_req",
        return_value={},
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": config_entry.entry_id},
            data=config_entry.data,
        )

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "authorize"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_USE_PSK: use_psk}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_PIN: new_pin}
        )

        assert result["type"] == data_entry_flow.FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"
        assert config_entry.data[CONF_PIN] == new_pin
