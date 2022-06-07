import os

ADMIN_ADDRESS = 0x032611AA4C7610D0B6306ADFFA27BF3E8774D1A27C3E9F93CDC2F7BCFEC0C3D7
ORACLE_CONTROLLER_ADDRESS = (
    0x013BEFE6EDA920CE4AF05A50A67BD808D67EEE6BA47BB0892BEF2D630EAF1BBA
)
PUBLISHER_REGISTRY_ADDRESS = (
    0x07E05E4DEA8A62988D9A06EA47BDAC34C759A413DB5B358E4A3A3D691D9D89E4
)
NETWORK = "testnet"
DEFAULT_AGGREGATION_MODE = 0

if os.environ.get("__PONTIS_STAGING_ENV__") == "TRUE":
    print("Warning: Communicating with staging contracts, not production")
    ORACLE_CONTROLLER_ADDRESS = (
        0x02F2A6FEFB5474490CF737DA1D1603F5914E525D3E4ABD8D87A8E139A864BAFF
    )
    PUBLISHER_REGISTRY_ADDRESS = (
        0x07CC3A9A4D1FE77B022E6E35007F0E1D8FDF8B87A8BDBCB2609C5D4E83817797
    )
