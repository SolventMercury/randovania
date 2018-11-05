import pprint
from random import Random
from typing import Tuple, List
from unittest.mock import MagicMock

import pytest

from randovania.game_description import data_reader
from randovania.game_description.node import ResourceNode
from randovania.games.prime import binary_data
from randovania.resolver.bootstrap import logic_bootstrap
from randovania.resolver.game_patches import GamePatches
from randovania.resolver.generator import get_actions_of_reach, gimme_reach_with_dangerous, _filter_pickups, _pickup_nodes_that_can_escape, gimme_reach, _state_with_pickup
from randovania.resolver.generator_explorer import PathDetail, GeneratorReach, filter_reachable, filter_pickup_nodes
from randovania.resolver.item_pool import calculate_item_pool, calculate_available_pickups
from randovania.resolver.layout_configuration import LayoutConfiguration, LayoutLogic, LayoutMode, LayoutRandomizedFlag, \
    LayoutEnabledFlag, LayoutDifficulty
from randovania.resolver.logic import Logic
from randovania.resolver.random_lib import shuffle
from randovania.resolver.state import State, add_resource_gain_to_state


@pytest.mark.parametrize(["old_path", "new_path", "expected"], [
    (PathDetail(True, 0), PathDetail(True, 0), False),
    (PathDetail(False, 0), PathDetail(False, 0), False),
    (PathDetail(True, 0), PathDetail(True, 1), False),
    (PathDetail(True, 5), PathDetail(False, 0), False),
    (PathDetail(False, 0), PathDetail(True, 5), True),
])
def test_is_path_better(old_path: PathDetail, new_path: PathDetail, expected: bool):
    assert new_path.is_better(old_path) == expected


def _test_data():
    data = binary_data.decode_default_prime2()
    game = data_reader.decode_data(data, [], False)
    configuration = LayoutConfiguration(logic=LayoutLogic.NO_GLITCHES,
                                        mode=LayoutMode.STANDARD,
                                        sky_temple_keys=LayoutRandomizedFlag.RANDOMIZED,
                                        item_loss=LayoutEnabledFlag.ENABLED,
                                        elevators=LayoutRandomizedFlag.VANILLA,
                                        hundo_guaranteed=LayoutEnabledFlag.DISABLED,
                                        difficulty=LayoutDifficulty.NORMAL,
                                        pickup_quantities={})

    patches = GamePatches({})
    logic, state = logic_bootstrap(configuration, game, patches)
    return logic, state


def _create_reaches_and_compare(logic: Logic, state: State,
                                patches: GamePatches,
                                ) -> Tuple[GeneratorReach, GeneratorReach]:
    first_reach = gimme_reach_with_dangerous(logic, state, patches)
    second_reach = gimme_reach_with_dangerous(logic, first_reach.state, patches)

    assert first_reach.is_safe_node(first_reach.state.node)
    assert second_reach.is_safe_node(first_reach.state.node)
    assert first_reach.is_safe_node(second_reach.state.node)
    assert second_reach.is_safe_node(second_reach.state.node)

    assert set(first_reach.safe_nodes) == set(second_reach.safe_nodes)
    assert set(first_reach.nodes) == set(second_reach.nodes)

    return first_reach, second_reach


def _compare_actions(first_reach: GeneratorReach,
                     second_reach: GeneratorReach,
                     ) -> Tuple[List[ResourceNode], List[ResourceNode]]:
    first_actions = get_actions_of_reach(first_reach)
    second_actions = get_actions_of_reach(second_reach)
    assert set(first_actions) == set(second_actions)

    return first_actions, second_actions


def test_calculate_reach_with_seeds():
    logic, state = _test_data()
    configuration = logic.configuration
    game = logic.game
    patches = logic.patches

    categories = {"translator", "major"}
    item_pool = calculate_item_pool(configuration, game)
    rng = Random(50000)
    available_pickups = tuple(shuffle(rng, sorted(calculate_available_pickups(
        item_pool, categories, game.relevant_resources))))

    remaining_pickups = available_pickups[-5:]

    print("Major items: {}".format([item.item for item in remaining_pickups]))

    for pickup in remaining_pickups[:]:
        add_resource_gain_to_state(state, pickup.resource_gain())

    first_reach, second_reach = _create_reaches_and_compare(logic, state, patches)
    first_actions, second_actions = _compare_actions(first_reach, second_reach)

    for action in first_actions:
        print("Safe: {}; Dangerous: {}; Action: {}".format(
            first_reach.is_safe_node(action),
            action.resource() in game.dangerous_resources,
            game.node_name(action)
        ))

    escape_state = _state_with_pickup(first_reach.state, available_pickups[-6])
    total_pickup_nodes = list(_filter_pickups(filter_reachable(first_reach.nodes, first_reach)))
    pickup_options = _pickup_nodes_that_can_escape(total_pickup_nodes,
                                                   gimme_reach(logic, escape_state, patches),
                                                   set(first_reach.safe_nodes))

    for option in pickup_options:
        print("Safe: {}; Dangerous: {}; Option: {}".format(
            first_reach.is_safe_node(option),
            option.resource() in game.dangerous_resources,
            game.node_name(option)
        ))

    assert (len(list(first_reach.nodes)), len(first_actions)) == (821, 1)
    assert (len(list(second_reach.nodes)), len(second_actions)) == (821, 1)


def test_calculate_reach_with_all_pickups():
    logic, state = _test_data()
    patches = logic.patches

    for pickup in logic.game.pickup_database.pickups:
        add_resource_gain_to_state(state, pickup.resource_gain())

    first_reach, second_reach = _create_reaches_and_compare(logic, state, patches)
    first_actions, second_actions = _compare_actions(first_reach, second_reach)

    found_pickups = set(filter_pickup_nodes(filter_reachable(second_reach.nodes, first_reach)))
    all_pickups = set(filter_pickup_nodes(logic.game.all_nodes))

    # assert (len(list(first_reach.nodes)), len(first_actions)) == (898, 9)
    # assert (len(list(second_reach.nodes)), len(second_actions)) == (898, 9)
    pprint.pprint(first_actions)
    assert found_pickups == all_pickups
