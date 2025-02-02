from random import Random

from randovania.game_description.db.dock import DockWeakness
from randovania.game_description.db.dock_node import DockNode
from randovania.game_description.game_description import GameDescription
from randovania.game_description.game_patches import GamePatches
from randovania.game_description.db.node_identifier import NodeIdentifier
from randovania.games.prime1.layout.prime_configuration import PrimeConfiguration
from randovania.generator.base_patches_factory import PrimeTrilogyBasePatchesFactory
from randovania.layout.base.base_configuration import BaseConfiguration


class PrimeBasePatchesFactory(PrimeTrilogyBasePatchesFactory):
    def create_base_patches(self,
                            configuration: BaseConfiguration,
                            rng: Random,
                            game: GameDescription,
                            is_multiworld: bool,
                            player_index: int,
                            rng_required: bool = True
                            ) -> GamePatches:
        assert isinstance(configuration, PrimeConfiguration)
        parent = super().create_base_patches(configuration, rng, game, is_multiworld, player_index, rng_required)

        nic = NodeIdentifier.create
        get_node = game.region_list.typed_node_by_identifier

        dock_weakness: list[tuple[DockNode, DockWeakness]] = []
        power_weak = game.dock_weakness_database.get_by_weakness("door", "Normal Door (Forced)")

        if configuration.main_plaza_door and not configuration.dock_rando.is_enabled():
            dock_weakness.append(
                (get_node(nic("Chozo Ruins", "Main Plaza", "Door from Plaza Access"), DockNode), power_weak),
            )

        if configuration.blue_save_doors:
            for area in game.region_list.all_areas:
                if area.extra.get("unlocked_save_station"):
                    for node in area.nodes:
                        if isinstance(node, DockNode) and node.dock_type.short_name == "door":
                            dock_weakness.append((node, power_weak))
                            # TODO: This is not correct in entrance rando
                            dock_weakness.append((get_node(node.default_connection, DockNode), power_weak))

        return parent.assign_dock_weakness(dock_weakness)
