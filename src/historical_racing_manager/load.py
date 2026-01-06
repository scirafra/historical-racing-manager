# TODO: rename to something like persistence? maybe does not make sense to separate this from the controller...
import pathlib


class LoadManager:
    """Handle saving and loading of all game data."""

    def save(self, folder: pathlib.Path, teams_model, series_model, drivers_model, manufacturer_model, contracts_model,
             race_model):
        """Save all game data to the given folder."""
        if folder:
            race_model.save(folder)
            contracts_model.save(folder)
            teams_model.save(folder)
            series_model.save(folder)
            drivers_model.save(folder)
            manufacturer_model.save(folder)

    def load_all(self, folder: pathlib.Path, series_model, teams_model, drivers_model, manufacturer_model,
                 contracts_model, race_model):
        """Load all game data into the provided model instances."""
        if folder:
            if not series_model.load(folder):
                print("Series not loaded")
                return False
            if not contracts_model.load(folder):
                print("Contracts not loaded")
                return False
            if not race_model.load(folder):
                print("Races not loaded")
                return False
            if not teams_model.load(folder):
                print("Teams not loaded")
                return False
            if not drivers_model.load(folder):
                print("Drivers not loaded")
                return False
            if not manufacturer_model.load(folder):
                print("Manufacturers not loaded")
                return False
            return True

        print("No name provided")
        return False
