def save(
    name, teams_model, series_model, drivers_model, manufacturer_model, contracts_model, race_model
):
    """Save all game data to the given folder."""
    if len(name) > 0:
        name = name + "/"
        race_model.save(name)
        contracts_model.save(name)
        teams_model.save(name)
        series_model.save(name)
        drivers_model.save(name)
        manufacturer_model.save(name)


def load_all(
    name, series_model, teams_model, drivers_model, manufacturer_model, contracts_model, race_model
):
    """Load all game data into the provided model instances."""
    if len(name) > 0:
        name = name + "/"

        if not series_model.load(name):
            print("Series not loaded")
            return False
        if not contracts_model.load(name):
            print("Contracts not loaded")
            return False
        if not race_model.load(name):
            print("Races not loaded")
            return False
        if not teams_model.load(name):
            print("Teams not loaded")
            return False
        if not drivers_model.load(name):
            print("Drivers not loaded")
            return False
        if not manufacturer_model.load(name):
            print("Manufacturers not loaded")
            return False

        return True
    else:
        print("No name provided")
        return False
