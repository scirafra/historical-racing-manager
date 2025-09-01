import contracts as co
import drivers as dr
import manufacturer as mf
import race as rc
import series as se
import teams as tm


def save(name):
    if len(name) > 0:
        name = name + "/"
        rc.save(name)
        co.save(name)
        tm.save(name)
        se.save(name)
        dr.save(name)
        mf.save(name)


def load_all(name):
    if len(name) > 0:
        name = name + "/"

        if not se.load(name):
            print("se not loaded")
            return False
        if not co.load(name):
            print("co not loaded")
            return False
        if not rc.load(name):
            print("rc not loaded")
            return False
        tmmodel = tm.TeamsModel()
        if not tmmodel.load(name):
            print("tm not loaded")
            return False
        drmodel = dr.DriversModel()
        if not drmodel.load(name):
            print("dr not loaded")
            return False
        if not mf.load(name):
            print("mf not loaded")
            return False

        return True
    else:
        print("Nezadal si meno")
        return False
