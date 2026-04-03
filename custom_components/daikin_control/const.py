DOMAIN = "daikin_control"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_INSTALLATION_ID = "installation_id"
CONF_SCAN_INTERVAL = "scan_interval"

BASE_URL = "https://www.daikin-control.com"
LOGIN_URL = f"{BASE_URL}/login_check"
PARAMETER_URL = f"{BASE_URL}/parameter"
PARAMETERNAME_URL = f"{BASE_URL}/parametername"

DEFAULT_SCAN_INTERVAL = 120  # seconds

# Parameter definitions: name -> (friendly_name, unit, device_class, icon)
PARAMETER_MAP = {
    "cAUSSENTEMP": ("Aussentemperatur", "\u00b0C", "temperature", "mdi:thermometer"),
    "cAUSSENTEMP_WAERMEPUMPE": ("Aussentemperatur WP", "\u00b0C", "temperature", "mdi:thermometer"),
    "cSPEICHERISTTEMP": ("Speicher Isttemperatur", "\u00b0C", "temperature", "mdi:thermometer-water"),
    "eVORLAUFISTTEMP": ("Vorlauf Isttemperatur", "\u00b0C", "temperature", "mdi:thermometer-chevron-up"),
    "eVORLAUFSOLLTEMP": ("Vorlauf Solltemperatur", "\u00b0C", "temperature", "mdi:thermometer-chevron-up"),
    "cKESSELISTTEMP": ("Kessel Isttemperatur", "\u00b0C", "temperature", "mdi:water-boiler"),
    "cKESSELSOLLTEMP": ("Kessel Solltemperatur", "\u00b0C", "temperature", "mdi:water-boiler"),
    "cRUECKLAUFTEMP": ("Ruecklauftemperatur", "\u00b0C", "temperature", "mdi:thermometer-chevron-down"),
    "cRAUMISTTEMP": ("Raum Isttemperatur", "\u00b0C", "temperature", "mdi:home-thermometer"),
    "cRAUMSOLLTEMP_I": ("Raum Solltemperatur I", "\u00b0C", "temperature", "mdi:home-thermometer-outline"),
    "cRAUMSOLLTEMP_II": ("Raum Solltemperatur II", "\u00b0C", "temperature", "mdi:home-thermometer-outline"),
    "cRAUMSOLLTEMP_III": ("Raum Solltemperatur III", "\u00b0C", "temperature", "mdi:home-thermometer-outline"),
    "cT_TVBH": ("TVBH Temperatur", "\u00b0C", "temperature", "mdi:thermometer"),
    "cT_TVBHMIX": ("TVBH Mix Temperatur", "\u00b0C", "temperature", "mdi:thermometer"),
    "cT_TVBH1": ("TVBH1 Temperatur", "\u00b0C", "temperature", "mdi:thermometer"),
    "cVOLUMENSTROM": ("Volumenstrom", "l/h", None, "mdi:water-pump"),
    "cPUMPENLAUFZEIT": ("Pumpenlaufzeit", "h", "duration", "mdi:pump"),
    "cKOMPRESSORLAUFZEIT": ("Kompressorlaufzeit", "h", "duration", "mdi:engine"),
    "cPROGRAMMSCHALTER": ("Programmschalter", None, None, "mdi:toggle-switch"),
    "cWW_AKTIV": ("Warmwasser aktiv", None, None, "mdi:water-boiler"),
    "cEINMAL_WW_AKTIV": ("Einmal Warmwasser aktiv", None, None, "mdi:water-boiler-alert"),
    "cFEHLER_AKTUELL": ("Aktueller Fehler", None, None, "mdi:alert-circle"),
    "eHZKKURVE": ("Heizkurve", None, None, "mdi:chart-line"),
    "eMAX_VORLAUFTEMP": ("Max Vorlauftemperatur", "\u00b0C", "temperature", "mdi:thermometer-high"),
    "eMAX_KUEHLEN_AUSSENTEMP_HZK0": ("Max Kuehlen Aussentemp", "\u00b0C", "temperature", "mdi:thermometer-low"),
    "cVERSTELLTE_SPEICHERSOLLTEMP": ("Verstellte Speicher Solltemp", "\u00b0C", "temperature", "mdi:thermometer-water"),
    "cEINSTELL_SPEICHERSOLLTEMP": ("Einstell Speicher Solltemp", "\u00b0C", "temperature", "mdi:thermometer-water"),
}
