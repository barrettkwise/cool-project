import pandas as pd
import pickle
from multiprocessing import Pool, cpu_count
from pathlib import PurePath

data_from_pickle = pickle.load(open(PurePath("nfl_data_to_transfer.pkl"), "rb"))

RAW_DATA_DIR = data_from_pickle.get("RAW_DATA_DIR")
CLEANED_DATA_DIR = data_from_pickle.get("CLEANED_DATA_DIR")
TOP_LEVEL_DIR = data_from_pickle.get("TOP_LEVEL_DIR")
stat_categories = data_from_pickle.get("stat_categories")
valid_directories = data_from_pickle.get("valid_directories")
college_data = data_from_pickle.get("college_data")


def add_player_id(directory: str) -> None:
    for category in stat_categories:
        file_path = PurePath(RAW_DATA_DIR / directory / f"{category}_modified.csv")
        df = pd.read_csv(file_path)
        players = df["Player"].tolist()
        matches = []
        for nfl_player in players:
            for cfb_player in college_data.keys():
                if cfb_player == nfl_player:
                    cfb_years = college_data[cfb_player]["player_stats"].keys()
                    if all(int(cfb_year) < int(directory) for cfb_year in cfb_years):
                        matches.append(
                            (college_data[cfb_player]["player_id"], nfl_player)
                        )
                        break
        matches_series = pd.Series(
            [match[0] for match in matches],
            index=[match[1] for match in matches],
            dtype=int,
        )
        try:
            df.insert(0, "Player ID", df["Player"].map(matches_series))
        except ValueError:
            df["Player ID"] = df["Player"].map(matches_series)
        df.to_csv(file_path, index=False)


def driver_function() -> None:
    with Pool(processes=cpu_count()) as pool:
        pool.map(add_player_id, valid_directories)


if __name__ == "__main__":
    driver_function()
