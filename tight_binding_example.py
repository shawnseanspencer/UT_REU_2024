import numpy as np
import matplotlib.pyplot as plt

# Tight-binding parameters
t = 360e-3  # eV
t_prime = -100e-3  # eV
t_double_prime = 35e-3  # eV
a_lattice = 3.85

#Square lattice
def dispersion_relation(kx, ky, lattice_constant):
    nearest_neighbor = -2 * t * (np.cos(lattice_constant*kx) + np.cos(lattice_constant*ky))
    next_nearest = -4 * t_prime * np.cos(lattice_constant*kx) * np.cos(lattice_constant*ky) 
    next_next_nearest = +t_double_prime * (np.cos(2 * lattice_constant*kx) + np.cos(2 * lattice_constant*ky))
    
    return nearest_neighbor + next_nearest + next_next_nearest

kx = np.linspace(-np.pi, np.pi, 100)/4
ky = np.linspace(-np.pi, np.pi, 100)/4
kx_grid, ky_grid = np.meshgrid(kx, ky)

fermi_energy = 0

# Compute the dispersion relation
ek = dispersion_relation(kx_grid, ky_grid, a_lattice)

plt.figure(figsize=(8, 6))
plt.contour(kx_grid, ky_grid, ek, levels=[fermi_energy])
plt.xlabel('kx')
plt.ylabel('ky')
plt.title(f'Fermi Surface (E_f = {fermi_energy} eV)')
plt.grid(True)

plt.show()
