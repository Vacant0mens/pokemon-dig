import requests
import json
import re


class PokeDig:
    def __init__(self, min_cp=2750, include_unevolved=False, include_evolutions=False,
                 include_mythical_legendary=False, only_mythical_and_legendary=False, get_all=False):
        self.min_cp = min_cp
        self.include_unevolved = include_unevolved
        self.include_evolutions = include_evolutions
        self.include_mythical_legendary = include_mythical_legendary
        self.only_mythical_and_legendary = only_mythical_and_legendary
        if self.only_mythical_and_legendary:
            self.include_mythical_legendary = True
            self.include_unevolved = True
        self.get_all = get_all
        if get_all:
            self.include_evolutions = False
        # all links returned in info are specific to db.pokemongohub.net, they have no affiliation to this code.
        self.api_base_url = "https://db.pokemongohub.net/api/pokemon/"
        self.pokemon_link_base_url = "https://db.pokemongohub.net/pokemon/"
        self.pokemon_image_base_url = "https://db.pokemongohub.net/images/official/full/"
        print("updating master file...")
        # master file content is downloaded from pokemongo-dev-contrib/pokemongo-game-master on github
        game_master_new = requests.get("https://raw.githubusercontent.com\
/pokemongo-dev-contrib/pokemongo-game-master/master/versions/latest/V2_GAME_MASTER.json").text
        # update local file
        with open("V2_GAME_MASTER.json", "w+") as master_file:
            master_file.write(game_master_new)
        print("done updating.")
        # read file into object
        with open("V2_GAME_MASTER.json", "r") as master_file:
            self.game_master = json.loads(master_file.read())
        # update local object with pokedex number/id, and max_cp
        game_master_list = self.game_master.get('template')
        self.poke_list = []
        for item in game_master_list:
            matcher = re.compile('^V\d{4}_POKEMON*')
            matched = matcher.match(item.get('templateId'))
            if matched is not None:
                poke_id = int(item.get("templateId").split('_')[0].replace("V", ""))
                # update pokedex number/id
                item.get('data').get('pokemon').update({"id": poke_id})
                max_cp = calculate_max_cp(attack=item.get('data').get('pokemon').get('stats').get('baseAttack'),
                                          defense=item.get('data').get('pokemon').get('stats').get('baseDefense'),
                                          stamina=item.get('data').get('pokemon').get('stats').get('baseStamina'))
                # update max_cp
                item.get('data').get('pokemon').update({"maxcp": max_cp})
                # add pokemon info to local object for processing
                info = self.get_pokemon_info(item.get('data').get('pokemon'))
                self.poke_list.append(info)
        self.chosen_list = {}

    def get_strong_pokemon(self):
        for pokemon in self.poke_list:
            chosen = False
            if pokemon.get('id') not in self.chosen_list:
                is_mythical_legendary = True if pokemon.get('class') == "Legendary" or \
                                                pokemon.get('class') == "Mythic" else False
                evolved_from = get_evolution(pokemon=pokemon)
                is_evolved = False if evolved_from == "-Unevolved-" else True
                if int(pokemon.get('maxcp')) >= self.min_cp:
                    chosen = True
                    if not is_evolved and not self.include_unevolved:
                        chosen = False
                    if is_mythical_legendary:
                        if not self.include_mythical_legendary:
                            chosen = False
                        else:
                            chosen = True
                    if self.only_mythical_and_legendary and not is_mythical_legendary:
                        chosen = False
                if self.get_all:
                    chosen = True
                    # print(len(chosen_list))
                if chosen:
                    self.update_chosen(pokemon=pokemon)
                    if self.include_evolutions:
                        self.update_chosen_evolutions(pokemon=pokemon)

        [print(json.dumps(self.chosen_list[chosen_one], indent=4)) for chosen_one in self.chosen_list]
        print(len(self.chosen_list))

    def update_chosen(self, pokemon: dict):
        self.chosen_list.update({pokemon.get('id'): pokemon})

    def get_pokemon_info(self, pokemon: dict) -> dict:
        if pokemon.get('parentId'):
            evolved_from = pokemon.get('parentId').title()
        else:
            family = '_'.join(pokemon.get('familyId').split('_')[1:]).title()
            pokemon_id = pokemon.get('uniqueId').title()
            evolution = pokemon.get('evolutionBranch')[0].get('evolution').title() \
                if pokemon.get('evolutionBranch') else ''
            if pokemon_id == family and not pokemon.get('candyToEvolve') and not pokemon.get('evolutionBranch'):
                evolved_from = "-Unevolved-"
            else:
                evolved_from = ''
        pokemon_class = pokemon.get('pokemonClass').split('_')[2].title()\
            if pokemon.get('pokemonClass') else "Normal"
        return {"id": pokemon.get('id'), "name": pokemon.get('uniqueId').title(), "maxcp": pokemon.get('maxcp'),
                "types": get_types(pokemon), "evolvedFrom": evolved_from.title(),
                "class": pokemon_class,
                "baseAttack": pokemon.get('stats').get('baseAttack'),
                "baseDefense": pokemon.get('stats').get('baseDefense'),
                "baseStamina": pokemon.get('stats').get('baseStamina'),
                "infoUrl": f"{self.pokemon_link_base_url}{pokemon.get('id')}",
                "imageUrl": f"{self.pokemon_image_base_url}{pokemon.get('id')}.png"}

    def update_chosen_evolutions(self, pokemon: dict):
        evolved_from = get_evolution(pokemon)
        poke2 = None
        while evolved_from:
            if not poke2:
                poke2 = next((pokes for pokes in self.poke_list
                              if evolved_from == pokes.get('name')), None)
            if poke2:
                self.update_chosen(poke2)
                evolved_from = get_evolution(poke2)
                if evolved_from:
                    poke2 = next((pokes for pokes in self.poke_list
                                  if evolved_from == pokes.get('name')), None)
                    if "Abra" == poke2.get('name'):
                        pass
                else:
                    poke2 = None
            else:
                print(f"Couldn't match {evolved_from} -----")
                evolved_from = None


def calculate_max_cp(attack, defense, stamina) -> int:
    return int(((attack + 15) * ((defense + 15) ** 0.5) * (stamina + 15) ** 0.5) * (0.7903 ** 2) / 10)


def get_evolution(pokemon: dict):
    return pokemon.get('evolvedFrom').title() if pokemon.get('evolvedFrom') \
                                                 and pokemon.get('evolvedFrom') != "-Unevolved-" else ''


def get_types(pokemon: dict) -> tuple:
    types = (pokemon.get('type1').split('_')[2].title(),
             pokemon.get('type2').split('_')[2].title())\
        if pokemon.get('type2') else (pokemon.get('type1').split('_')[2].title(),)
    return types


if __name__ == '__main__':
    # poke_dig = PokeDig(include_evolutions=True, include_unevolved=True)  # include_mythical_legendary=True)
    poke_dig = PokeDig(only_mythical_and_legendary=True)
    poke_dig.get_strong_pokemon()
