import numpy as np

class GlobalSymbols(dict):
    def __init__(self, data):
        super(GlobalSymbols, self).__init__()
        self['np'] = np
        for k,v in data.items():
            self['c_'+k] = v

def add_constant(name, val):
    pom_globals['c_'+name] = val

def list_constants():
    for k,v in pom_globals.items():
        if k.find('c_') == 0:
            print(k[2:],v)

pom_globals = GlobalSymbols({
                  'c': 2.99792458e8, # speed of light (m/s)
                  'h': 6.6260755e-34, # Planck constant (Js)
                  'heV': 4.135667516e-15, # Planck constant (eVs)
                  'kb': 1.380658e-23, # Boltzmann constant (J/K)
                  'e': 1.60217733e-19, # elementary charge (C)
                  'mu0': 12.566370614e-7, # magnetic permeability (T^2m^3/J)
                  'eps0': 8.854187817e-12, # electric field constant (C^2/Jm)
                  'Ry': 13.60569253, # Rydberg constant (eV)
                  'sigma': 5.670373e-8, # Stefan Boltzmann constant (W m-2 K-4)
                  'm0': 9.10938215e-31, # electron mass (kg)
                  'pi': np.pi})

