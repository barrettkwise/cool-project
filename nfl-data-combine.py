import pandas as pd
import pickle
import json
from multiprocessing import Pool, cpu_count
from pathlib import PurePath

data_from_pickle = pickle.load(open(PurePath("nfl_data_to_transfer.pkl"), "rb"))

RAW_DATA_DIR = data_from_pickle.get("RAW_DATA_DIR")
CLEANED_DATA_DIR = data_from_pickle.get("CLEANED_DATA_DIR")
TOP_LEVEL_DIR = data_from_pickle.get("TOP_LEVEL_DIR")
stat_categories = data_from_pickle.get("stat_categories")
valid_directories = data_from_pickle.get("valid_directories")
college_data = data_from_pickle.get("college_data")

bad_stat_types = [
    "QBrec",
    "Cmp%",
    "Y/A",
    "AY/A",
    "ANY/A",
    "Rate",
    "TD%",
    "Int%",
    "Y/R",
    "Y/C",
    "Y/Tgt",
    "Ctch%",
    "R/G",
    "Y/G",
    "A/G",
    "Sk%",
    "XP%",
    "FG%",
    "NY/A",
    "NY/P",
    "Y/P",
    "Y/Ret",
    "Y/Ret.1",
    "KOAvg",
    "TB%",
    "In20%",
    "Succ%",
    "QBR",
]


def preload_all_data() -> dict:
    player_index = {}

    for season in range(2004, 2025):
        for category in stat_categories:
            file_path = PurePath(
                RAW_DATA_DIR / f"{season}" / f"{category}_modified.csv"
            )
            df = pd.read_csv(file_path)

            for _, row in df.iterrows():
                player = row["Player"]
                row_dict = row.to_dict()
                row_dict.pop("Player", None)
                row_dict.pop("Player ID", None)
                row_dict.pop("Team", None)
                row_dict.pop("Pos", None)
                row_dict.pop("Age", None)
                row_dict.pop("G", None)
                row_dict.pop("GS", None)

                if player not in player_index:
                    player_index[player] = {
                        "player_id": row["Player ID"],
                        "years_played": 0,
                        "age": int(row["Age"]),
                        "team": row["Team"],
                        "position": row["Pos"],
                        "player_stats": {season: {"games_played": row["G"]}},
                    }
                elif season not in player_index[player]["player_stats"]:
                    player_index[player]["player_stats"][season] = {
                        "games_played": row["G"]
                    }
                    player_index[player]["years_played"] += 1

                player_index[player]["player_stats"][season][category] = {
                    "long"
                    if stat.lower() == "lng"
                    else stat.lower()
                    if "." not in stat
                    else stat.split(".")[0].lower(): row_dict[stat]
                    for stat in row_dict.keys()
                    if stat not in bad_stat_types
                }

    return player_index


player_index = preload_all_data()
all_players = list(player_index.keys())


def add_player_data(player_name: str) -> tuple[str, dict]:
    player_data = player_index.get(player_name, {})
    return player_name, player_data


def driver_function() -> None:
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(add_player_data, all_players)

    cumm_player_data = dict(results)

    with open(PurePath(CLEANED_DATA_DIR / "nfl_player_data.json"), "w") as f:
        json.dump(cumm_player_data, f, indent=2)


if __name__ == "__main__":
    driver_function()
