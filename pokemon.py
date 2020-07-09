import requests
import json
import re


class PokeDig:
    def __init__(self, min_cp=2750, must_be_evolved=False, include_mythical_legendary=False, include_evolutions=True):
        self.min_cp = min_cp
        self.is_evolved = must_be_evolved
        self.include_mythical_legendary = include_mythical_legendary
        self.include_evolutions = include_evolutions
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
                self.poke_list.append(item.get('data').get('pokemon'))
        self.chosen_list = {}

    def get_strong_pokemon(self):
        for poke in self.poke_list:
            chosen = False
            if poke.get('id') not in self.chosen_list:
                is_mythical_legendary = bool(poke.get('pokemonClass'))
                evolved_from = get_evolution(poke)
                is_evolved = bool(evolved_from)
                if int(poke.get('maxcp')) >= self.min_cp:
                    chosen = True
                    if is_evolved:
                        if not self.is_evolved:
                            chosen = False
                    if is_mythical_legendary:
                        if not self.include_mythical_legendary:
                            chosen = False
                    # print(len(chosen_list))
                if chosen:
                    self.update_chosen(poke)
                    if self.include_evolutions:
                        self.update_chosen_evolutions(poke)

        print(len(self.chosen_list))
        [print(json.dumps(self.chosen_list[chosen_one], indent=4)) for chosen_one in self.chosen_list]

    def update_chosen(self, pokemon: dict):
        poke_info = self.get_pokemon_info(pokemon)
        self.chosen_list.update({pokemon.get('id'): poke_info})

    def get_pokemon_info(self, pokemon: dict) -> dict:
        evolved_from = pokemon.get('parentId').title() if pokemon.get('parentId') else ""
        return {"id": pokemon.get('id'), "name": pokemon.get('uniqueId').title(), "maxcp": pokemon.get('maxcp'),
                "types": get_types(pokemon), "evolvedFrom": evolved_from.title(),
                "infoUrl": f"{self.pokemon_link_base_url}{pokemon.get('id')}",
                "imageUrl": f"{self.pokemon_image_base_url}{pokemon.get('id')}.png"}

    def update_chosen_evolutions(self, pokemon: dict):
        evolved_from = get_evolution(pokemon)
        poke2 = None
        while evolved_from:
            if not poke2:
                poke2 = next((pokes for pokes in self.poke_list
                              if evolved_from == pokes.get('uniqueId').strip().title()), None)
            if poke2:
                self.update_chosen(poke2)
                evolved_from = get_evolution(poke2)
                if evolved_from:
                    poke2 = next((pokes for pokes in self.poke_list
                                  if evolved_from == pokes.get('uniqueId').strip().title()), None)
                else:
                    poke2 = None
            else:
                print(f"Couldn't match {evolved_from} -----")
                evolved_from = None


def calculate_max_cp(attack, defense, stamina) -> int:
    return int(((attack + 15) * ((defense + 15) ** 0.5) * (stamina + 15) ** 0.5) * (0.7903 ** 2) / 10)


def get_evolution(pokemon: dict):
    return pokemon.get('parentId').title() if pokemon.get('parentId') else ''


def get_types(pokemon: dict) -> tuple:
    types = (pokemon.get('type1').split('_')[2].title(),
             pokemon.get('type2').split('_')[2].title())\
        if pokemon.get('type2') else (pokemon.get('type1').split('_')[2].title(),)
    return types


if __name__ == '__main__':
    poke_dig = PokeDig(must_be_evolved=True, include_mythical_legendary=False)
    poke_dig.get_strong_pokemon()
