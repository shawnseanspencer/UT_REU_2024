import re

def filter_meta_data(ls):
    """Helps with text processing in load_xy function.
    Sorts list of strings into key:value pairs"""
    
    ls = list(map(lambda string: re.split(r'(\s\s)+', string), ls))
    ls_dict = {}
    for i in range(len(ls)):
        ls[i] = [string for string in ls[i] if not re.fullmatch(r'\s*', string)]
        ls[i] = [re.sub('^#', '', string) for string in ls[i]]
        if len(ls[i]) > 2:
            ls[i].pop(0)
        
        ls[i] = [re.sub(r'\s+', '', string) for string in ls[i]]
            
        try:
            ls_dict[ls[i][0]] = ls[i][1]
        except IndexError:
            None
    return ls_dict
    
def load_xy(file_path, ONLY_SETTINGS=False, ONLY_GROUPNAMES=False):
    """Loads .xy file from SPECS setup in Baldini Lab into Python dictionary format.
    Output is best used in 'load_xarray' function to extract data from 
    a specific trial run(EDC, FS, etc.)
    Args:
        file_path: The SPECS output file (MUST BE IN .xy FORMAT)
        ONLY_SETTINGS: If true will output only the experiment universal settings (useful for documentation)
        ONLY_GROUPNAMES: If true will outut only names of each group (used in other functions)"""
    
    with open(file_path) as file:
        lines = file.readlines()

    lines = [l.strip() for l in lines]
    settings_index = lines.index("#   Time Zone Format:         UTC")
    settings = filter_meta_data(lines[:settings_index+1])

    if ONLY_SETTINGS:
        return settings

    #GROUP DEPENDENT DATA AND METADATA
    meta_data = lines[settings_index+2:] #Everything after the settings
    data = np.loadtxt(file_path)

    group_count = sum('Group' in string for string in meta_data)
    group_indexes = [index for index, string in enumerate(meta_data) if 'Group' in string]
    group_names = []
    for index in group_indexes:
        idx = meta_data[index].rfind('    ')
        group_names.append(meta_data[index][idx+1:].strip())
        
    if ONLY_GROUPNAMES == True:
        return group_names
        
    group_datas = []
    for i in range(len(group_indexes)):
        try:
            group_datas.append(meta_data[group_indexes[i]:group_indexes[i+1]])
        except IndexError:
            group_datas.append(meta_data[group_indexes[i]:])

    groups = dict(zip(group_names, group_datas))
    trial_settings = []
    
    for key in groups.keys():
        groups[key].pop(-1) #There was whitespace at end of each list
        group = groups[key]
        
        #OR for "OrdinateRange", and R for 'Region'. Slices out group dependent settings values
        group_OR_indexes = [index+3 for index, string in enumerate(group) if 'OrdinateRange:' in string] #Stripping messes with the indexes a bit, hence the + 
        group_R_indexes = [index for index, string in enumerate(group) if 'Region:' in string]

        #Just the data sets with their numbered labels
        #And filtering out group dependent meta data besides numbered labels
        trials = []
        run_settings = dict()
        if len(group_OR_indexes) == 1:
            trials.append(group[group_OR_indexes[0]+2:])
            run_settings['Trial 1'] = filter_meta_data(group[:group_OR_indexes[0]])
        else:
            for i in range(len(group_OR_indexes)):
                run_settings[f'Trial {i+1}'] = filter_meta_data(group[group_R_indexes[i]:group_OR_indexes[i]])
                try:                     
                    trials.append(group[group_OR_indexes[i]+2:group_R_indexes[i+1]-1])
                except IndexError:
                    trials.append(group[group_OR_indexes[i]+2:])    

        trial_datas = dict()
        count = 0
        for i, trial in enumerate(trials):
            cycle_curve_dict = dict()
            cycle_curve_data = []
            cycle_curve_params = []
            coordinates = ''
            cycle_names = ['Cycle: 0, Curve: 0'] #Initializing for first parse through
            for line in trial:
                try:
                    if "Cycle:" in line:
                        cycle_names.append(line[2:])
                        cycle_curve_dict[cycle_names[0]] = [filter_meta_data(cycle_curve_params), np.array(cycle_curve_data)]

                        #Making sure coordinates have a space in between them
                        if len(cycle_curve_params) > 3:
                            #Note, I leave it as a string, as there may be whitespace in the coordinate names
                            coordinates = cycle_curve_params[-2].split('   ')[-1].strip()
                            
                        cycle_names.pop(0)
                        cycle_curve_data, cycle_curve_params = [], []
                    if line[0] == '#':
                        cycle_curve_params.append(line[2:])
                    elif line[0] != '#':
                        numbers = line.split('  ')
                        cycle_curve_data.append([float(numbers[0]), float(numbers[1])])
                except IndexError:
                    None

            #Making sure coordinates have a space in between them

            for k in cycle_curve_dict.keys():
                cycle_curve_dict[k][0]['ColumnLabels:'] = coordinates
                
            trial_datas[f'Trial {i+1}'] = cycle_curve_dict

        for k in run_settings.keys():
            run_settings[k].update(trial_datas[k])
        
        groups[key] = run_settings


    return {
        'settings': settings,
        'groups': groups,
    }

#Loading Data into Xarray
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

def load_to_xarray(data, group_name, trial_name):
    """Takes output of load_xy function and outputs xarray of desired trial.
    Args:
        data: The whole output of load_xy(file)
        group_name: Name of desired group
        trial_name: Name of desired trial within group"""

    #Error handling if group_name or trial_name is invalid
    try:
        group = data['groups'][group_name]
    except KeyError:
        groups  = []
        for group in data['groups'].keys():
            groups.append(group)
        print(f"""Group name not in data provided. Please choose from one of the following groups:
        {groups}""")
        return 1
    try:
        trial = group[trial_name]
    except KeyError:
        trials  = []
        for trial in group.keys():
            trials.append(trial)
        print(f"""Trial name not in data provided. Please choose from one of the following trials:
        {trials}""")
        return 2

    #Updating universal settings with trial specific settings
    settings = data['settings']
    for key, value in trial.items():
        if type(trial[key]) == list:
            continue
        else:
            settings.update({key:value})

    #Loading data into numpy array
    cuts = []
    array = []
    cuts = []
    cycle = 0
    one_cut = False
    for key, value in trial.items():
        #Only 1 cut
        if len(list(trial.keys())) < 500:
            one_cut = True
            if type(value) != list:
                continue
            elif len(trial[key][1]) == 0:
                continue
            else:
                array.append(trial[key][1])
            continue

        #More than one cut
        elif type(value) != list:
            continue
        else:
            if len(trial[key][1]) == 0:
                continue
            elif int(re.sub(',', '', key[7:9])) == cycle:
                array.append(trial[key][1])
            elif int(re.sub(',', '', key[7:9])) == cycle+1:
                cycle += 1
                cuts.append(array)
                array = [trial[key][1]]

    #SUPER Messy solution to 1 off error
    groups = data['groups']
    new_key = str(list(groups[list(groups.keys())[-1]].keys())[-1])
    next_key = str(list(groups[list(groups.keys())[-1]][new_key].keys())[-1])
    final_curve = groups[list(groups.keys())[-1]][new_key][next_key][1]

    cuts.append(array) #Appending final array as the loop doesn't get to it
        
    if len(cuts[-2]) != len(cuts[-1]): #Sometimes the last item gets cut off
        cuts[-1].append(final_curve)
        
    print(len(cuts[-1]))
    cuts = np.array(cuts)[:, :, :, 1] #0th dimension is just the scan variable
    print(cuts.shape)

    #BEGIN LOADING INTO XARRAY
    scan_var = trial[list(trial.keys())[-1]][0]['ColumnLabels:'].split(' ')[0].strip()
    scan_var_coords = settings['OrdinateRange:'].strip()[1:len(settings['OrdinateRange:'])-1].split(',')
    scan_var_coords = [float(val) for val in scan_var_coords]

    #Interpreting NonEnergyOrdinate from imaging mode
    if 'MM_Momentum' in settings['AnalyzerLens:']:
        non_energy_ordinate = 'k_y'
    non_energy_ordinate_coords = [
        float(trial['Cycle: 0, Curve: 0'][0]['NonEnergyOrdinate:']),
        float(trial[str(list(trial.keys())[-1])][0]['NonEnergyOrdinate:'])
    ]

    #Getting rid of whitespace in coordinate names
    cycle_dimension_name = re.sub(r'\s+','_',group_name.strip())
    
    spectrum = xr.DataArray(
        data = cuts,
        dims = [cycle_dimension_name, scan_var, non_energy_ordinate],
        coords = {
            cycle_dimension_name: np.linspace(0, 10, cuts.shape[0]),
            scan_var: np.linspace(scan_var_coords[0], scan_var_coords[1], cuts.shape[1]),
            non_energy_ordinate: np.linspace(non_energy_ordinate_coords[0], non_energy_ordinate_coords[1], cuts.shape[2])
        },
        attrs = settings
    )
    
    # plt.scatter(cuts[0, :, 1], np.array(sum(cuts)[:, 0]))

    return spectrum

spectrum = load_to_xarray(test, 'stig M1', 'Trial 1')

