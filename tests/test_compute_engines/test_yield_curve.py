import pytest
import pytest_asyncio
from pontis.core.entry import construct_entry, serialize_entry
from pontis.core.utils import str_to_felt
from starkware.starknet.business_logic.state.state import BlockInfo
from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.testing.starknet import Starknet
from test_compute_engines.yield_curve import (
    calculate_future_spot_yield_point,
    calculate_on_yield_point,
)
from utils import assert_event_emitted, cached_contract, construct_path

# The path to the contract source code.
PUBLISHER_REGISTRY_CONTRACT_FILE = construct_path(
    "contracts/publisher_registry/PublisherRegistry.cairo"
)
ORACLE_CONTROLLER_CONTRACT_FILE = construct_path(
    "contracts/oracle_controller/OracleController.cairo"
)
ORACLE_IMPLEMENTATION_CONTRACT_FILE = construct_path(
    "contracts/oracle_implementation/OracleImplementation.cairo"
)
YIELD_CURVE_CONTRACT_FILE = construct_path("contracts/compute_engines/YieldCurve.cairo")
ACCOUNT_CONTRACT_FILE = construct_path("contracts/account/Account.cairo")
DEFAULT_DECIMALS = 18
AGGREGATION_MODE = 0
STARKNET_STARTING_TIMESTAMP = 1650590820
ON_KEY = "aave-on-borrow"
SPOT_KEY = "btc/usd"
FUTURE_KEYS = {"btc/usd-20220624": 1656043200, "btc/usd-20220930": 1664510400}


@pytest_asyncio.fixture(scope="module")
async def contract_classes():
    account_class = compile_starknet_files(
        files=[ACCOUNT_CONTRACT_FILE], debug_info=True
    )
    publisher_registry_class = compile_starknet_files(
        files=[PUBLISHER_REGISTRY_CONTRACT_FILE],
        debug_info=True,
    )
    oracle_controller_class = compile_starknet_files(
        files=[ORACLE_CONTROLLER_CONTRACT_FILE],
        debug_info=True,
    )
    oracle_implementation_class = compile_starknet_files(
        files=[ORACLE_IMPLEMENTATION_CONTRACT_FILE],
        debug_info=True,
    )
    yield_curve_class = compile_starknet_files(
        files=[YIELD_CURVE_CONTRACT_FILE],
        debug_info=True,
        disable_hint_validation=True,
    )
    return (
        account_class,
        publisher_registry_class,
        oracle_controller_class,
        oracle_implementation_class,
        yield_curve_class,
    )


@pytest_asyncio.fixture(scope="module")
async def contract_init(
    contract_classes, private_and_public_admin_keys, private_and_public_publisher_keys
):
    _, admin_public_key = private_and_public_admin_keys
    _, publisher_public_key = private_and_public_publisher_keys
    (
        account_class,
        publisher_registry_class,
        oracle_controller_class,
        oracle_implementation_class,
        yield_curve_class,
    ) = contract_classes

    starknet = await Starknet.empty()
    starknet.state.state.block_info = BlockInfo.create_for_testing(
        starknet.state.state.block_info.block_number, STARKNET_STARTING_TIMESTAMP
    )
    admin_account = await starknet.deploy(
        contract_class=account_class, constructor_calldata=[admin_public_key]
    )
    publisher_account = await starknet.deploy(
        contract_class=account_class, constructor_calldata=[publisher_public_key]
    )
    publisher_registry = await starknet.deploy(
        contract_class=publisher_registry_class,
        constructor_calldata=[admin_account.contract_address],
    )
    oracle_controller = await starknet.deploy(
        contract_class=oracle_controller_class,
        constructor_calldata=[
            admin_account.contract_address,
            publisher_registry.contract_address,
        ],
    )
    oracle_implementation = await starknet.deploy(
        contract_class=oracle_implementation_class,
        constructor_calldata=[oracle_controller.contract_address],
    )
    yield_curve = await starknet.deploy(
        contract_class=yield_curve_class,
        constructor_calldata=[
            admin_account.contract_address,
            oracle_controller.contract_address,
        ],
    )

    return {
        "starknet": starknet,
        "admin_account": admin_account,
        "publisher_account": publisher_account,
        "publisher_registry": publisher_registry,
        "oracle_controller": oracle_controller,
        "oracle_implementation": oracle_implementation,
        "yield_curve": yield_curve,
    }


@pytest.fixture
def contracts(contract_classes, contract_init):
    (
        account_class,
        publisher_registry_class,
        oracle_controller_class,
        oracle_implementation_class,
        yield_curve_class,
    ) = contract_classes
    _state = contract_init["starknet"].state.copy()
    admin_account = cached_contract(
        _state, account_class, contract_init["admin_account"]
    )
    publisher_account = cached_contract(
        _state, account_class, contract_init["publisher_account"]
    )
    publisher_registry = cached_contract(
        _state, publisher_registry_class, contract_init["publisher_registry"]
    )
    oracle_controller = cached_contract(
        _state, oracle_controller_class, contract_init["oracle_controller"]
    )
    oracle_implementation = cached_contract(
        _state, oracle_implementation_class, contract_init["oracle_implementation"]
    )
    yield_curve = cached_contract(
        _state,
        yield_curve_class,
        contract_init["yield_curve"],
    )
    return {
        "starknet": contract_init["starknet"],
        "admin_account": admin_account,
        "publisher_account": publisher_account,
        "publisher_registry": publisher_registry,
        "oracle_controller": oracle_controller,
        "oracle_implementation": oracle_implementation,
        "yield_curve": yield_curve,
    }


@pytest_asyncio.fixture
async def initialized_contracts(
    contracts,
    admin_signer,
    publisher,
):
    admin_account = contracts["admin_account"]
    publisher_account = contracts["publisher_account"]
    publisher_registry = contracts["publisher_registry"]
    oracle_controller = contracts["oracle_controller"]
    oracle_implementation = contracts["oracle_implementation"]
    yield_curve = contracts["yield_curve"]

    # Register publisher
    await admin_signer.send_transaction(
        admin_account,
        publisher_registry.contract_address,
        "register_publisher",
        [publisher, publisher_account.contract_address],
    )

    # Add oracle implementation address to controller
    tx_exec_info = await admin_signer.send_transaction(
        admin_account,
        oracle_controller.contract_address,
        "add_oracle_implementation_address",
        [oracle_implementation.contract_address],
    )
    assert_event_emitted(
        tx_exec_info,
        oracle_controller.contract_address,
        "AddedOracleImplementation",
        [oracle_implementation.contract_address],
    )

    await admin_signer.send_transaction(
        admin_account,
        yield_curve.contract_address,
        "add_on_key",
        [str_to_felt(ON_KEY), 1],
    )

    await admin_signer.send_transaction(
        admin_account,
        yield_curve.contract_address,
        "add_spot_key",
        [str_to_felt(SPOT_KEY), 1],
    )

    for future_key, future_expiry_timestamp in FUTURE_KEYS.items():
        await admin_signer.send_transaction(
            admin_account,
            yield_curve.contract_address,
            "add_future_key",
            [
                str_to_felt(SPOT_KEY),
                str_to_felt(future_key),
                1,
                future_expiry_timestamp,
            ],
        )

    return contracts


@pytest.mark.asyncio
async def test_deploy(initialized_contracts):
    yield_curve = initialized_contracts["yield_curve"]

    on_keys = await yield_curve.get_on_keys().call()
    assert [str_to_felt(ON_KEY)] == on_keys.result.on_keys

    on_key_is_active = await yield_curve.get_on_key_is_active(
        str_to_felt(ON_KEY)
    ).call()
    assert on_key_is_active.result.on_key_is_active == 1

    spot_keys = await yield_curve.get_spot_keys().call()
    assert [str_to_felt(SPOT_KEY)] == spot_keys.result.spot_keys

    spot_key_is_active = await yield_curve.get_spot_key_is_active(
        str_to_felt(SPOT_KEY)
    ).call()
    assert spot_key_is_active.result.spot_key_is_active == 1

    future_keys = await yield_curve.get_future_keys(str_to_felt(SPOT_KEY)).call()
    assert [
        str_to_felt(k) for k in FUTURE_KEYS.keys()
    ] == future_keys.result.future_keys

    return


@pytest.mark.asyncio
async def test_empty_yield_curve(initialized_contracts, publisher_signer, publisher):
    yield_curve = initialized_contracts["yield_curve"]

    # Call get_yield_curve and check result
    result = await yield_curve.get_yield_points(10).call()
    assert len(result.result.yield_points) == 0

    return


@pytest.mark.asyncio
async def test_yield_curve(initialized_contracts, publisher_signer, publisher):
    publisher_account = initialized_contracts["publisher_account"]
    oracle_controller = initialized_contracts["oracle_controller"]
    yield_curve = initialized_contracts["yield_curve"]

    output_decimals = 10

    # Submit data (on, spot, futures)
    on_entry = construct_entry(
        key=ON_KEY,
        value=1 * (10**15),  # 0.1% at 18 decimals (default),
        timestamp=STARKNET_STARTING_TIMESTAMP,
        publisher=publisher,
    )
    await publisher_signer.send_transaction(
        publisher_account,
        oracle_controller.contract_address,
        "submit_entry",
        serialize_entry(on_entry),
    )

    spot_entry = construct_entry(
        key=SPOT_KEY,
        value=100,
        timestamp=STARKNET_STARTING_TIMESTAMP,
        publisher=publisher,
    )
    await publisher_signer.send_transaction(
        publisher_account,
        oracle_controller.contract_address,
        "submit_entry",
        serialize_entry(spot_entry),
    )

    yield_points = [
        calculate_on_yield_point(
            on_entry.value, on_entry.timestamp, DEFAULT_DECIMALS, output_decimals
        ),
    ]

    for future_key, future_expiry_timestamp in FUTURE_KEYS.items():
        future_entry = construct_entry(
            key=future_key,
            value=110,
            timestamp=STARKNET_STARTING_TIMESTAMP,
            publisher=publisher,
        )
        await publisher_signer.send_transaction(
            publisher_account,
            oracle_controller.contract_address,
            "submit_entry",
            serialize_entry(future_entry),
        )
        yield_points.append(
            calculate_future_spot_yield_point(
                future_entry.value,
                future_entry.timestamp,
                future_expiry_timestamp,
                spot_entry.value,
                spot_entry.timestamp,
                DEFAULT_DECIMALS,
                DEFAULT_DECIMALS,
                output_decimals,
                current_timestamp=STARKNET_STARTING_TIMESTAMP,
            )
        )

    # Call get_yield_curve and check result
    result = await yield_curve.get_yield_points(output_decimals).call()
    assert result.result.yield_points == yield_points

    return