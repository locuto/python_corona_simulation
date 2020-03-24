'''
this file contains all functions required in computing
new infections, recoveries, and deaths
'''

import numpy as np

from motion import get_motion_parameters

def infect(population, pop_size, infection_range, infection_chance, frame, 
           healthcare_capacity, verbose, send_to_location=False,
           location_bounds=[], destinations=[], location_no=1, location_odds=1.0,
           traveling_infects=True):
    '''finds new infections'''

    #find new infections
    infected_previous_step = population[population[:,6] == 1]

    new_infections = []

    #if less than half are infected, slice based on infected (to speed up computation)
    if len(infected_previous_step) < (pop_size // 2):
        for patient in infected_previous_step:
            #define infection zone for patient
            infection_zone = [patient[1] - infection_range, patient[2] - infection_range,
                              patient[1] + infection_range, patient[2] + infection_range]

            #find healthy people surrounding infected patient
            if traveling_infects or patient[11] == 0:
                indices = np.int32(population[:,0][(infection_zone[0] < population[:,1]) & 
                                                   (population[:,1] < infection_zone[2]) &
                                                   (infection_zone[1] < population [:,2]) & 
                                                   (population[:,2] < infection_zone[3]) &
                                                   (population[:,6] == 0)])
            else:
                indices = []

            for idx in indices:
                #roll die to see if healthy person will be infected
                if np.random.random() < infection_chance:
                    population[idx][6] = 1
                    population[idx][8] = frame
                    if len(population[population[:,10] == 1]) <= healthcare_capacity:
                        if send_to_location:
                            #send to location if die roll is positive
                            if np.random.uniform() <= location_odds:
                                population[idx][10] = 1
                                population[idx],\
                                destinations[idx] = go_to_location(population[idx],
                                                                   destinations[idx],
                                                                   location_bounds, 
                                                                   dest_no=location_no)
                    new_infections.append(idx)

    else:
        #if more than half are infected slice based in healthy people (to speed up computation)
        healthy_previous_step = population[population[:,6] == 0]
        for person in healthy_previous_step:
            #define infecftion range around healthy person
            infection_zone = [person[1] - infection_range, person[2] - infection_range,
                              person[1] + infection_range, person[2] + infection_range]

            if person[6] == 0: #if person is not already infected, find if infected are nearby
                #find infected nearby healthy person
                if traveling_infects:
                    poplen = len(population[:,6][(infection_zone[0] < population[:,1]) & 
                                 (population[:,1] < infection_zone[2]) &
                                 (infection_zone[1] < population [:,2]) & 
                                 (population[:,2] < infection_zone[3]) &
                                 (population[:,6] == 1)])
                else:
                    poplen = len(population[:,6][(infection_zone[0] < population[:,1]) & 
                                 (population[:,1] < infection_zone[2]) &
                                 (infection_zone[1] < population [:,2]) & 
                                 (population[:,2] < infection_zone[3]) &
                                 (population[:,6] == 1) &
                                 (population[:,11] == 0)])

                    if np.random.random() <= infection_chance:
                        #roll die to see if healthy person will be infected
                        population[np.int32(person[0])][6] = 1
                        population[np.int32(person[0])][8] = frame
                        if len(population[population[:,10] == 1]) <= healthcare_capacity:
                            if send_to_location:
                                #send to location and add to treatment if die roll is positive
                                if np.random.uniform() < location_odds:
                                    population[np.int32(person[0])][10] = 1
                                    population[np.int32(person[0])],\
                                    destinations[np.int32(person[0])] = go_to_location(population[np.int32(person[0])],
                                                                                       destinations[np.int32(person[0])],
                                                                                       location_bounds, 
                                                                                       dest_no=location_no)


                        new_infections.append(np.int32(person[0]))

    if len(new_infections) > 0 and verbose:
        print('at timestep %i these people got sick: %s' %(frame, new_infections))

    if len(destinations) == 0:
        return population
    else:
        return population, destinations


def recover_or_die(population, frame, recovery_duration, mortality_chance, 
                   risk_age, critical_age, critical_mortality_chance, 
                   risk_increase, no_treatment_factor, age_dependent_risk,
                   treatment_dependent_risk, treatment_factor, verbose):
    '''see whether to recover or die

    '''

    #find sick people
    sick_people = population[population[:,6] == 1]

    #define vector of how long everyone has been sick
    illness_duration_vector = frame - sick_people[:,8]
    
    recovery_odds_vector = (illness_duration_vector - recovery_duration[0]) / np.ptp(recovery_duration)
    recovery_odds_vector = np.clip(recovery_odds_vector, a_min = 0, a_max = None)

    #update states of sick people 
    indices = sick_people[:,0][recovery_odds_vector >= sick_people[:,9]]

    cured = []
    died = []

    #decide whether to die or recover
    for idx in indices:
        #check if we want risk to be age dependent
        #if age_dependent_risk:
        if age_dependent_risk:
            updated_mortality_chance = compute_mortality(sick_people[sick_people[:,0] == idx][:,7][0], 
                                                         mortality_chance,
                                                         risk_age, critical_age, 
                                                         critical_mortality_chance, 
                                                         risk_increase)
        else:
            updated_mortality_chance = mortality_chance

        if sick_people[sick_people[:,0] == int(idx)][:,10] == 0 and treatment_dependent_risk:
            #if person is not in treatment, increase risk by no_treatment_factor
            updated_mortality_chance = updated_mortality_chance * no_treatment_factor
        elif sick_people[sick_people[:,0] == int(idx)][:,10] == 1 and treatment_dependent_risk:
            #if person is in treatment, decrease risk by 
            updated_mortality_chance = updated_mortality_chance * treatment_factor

        if np.random.random() <= updated_mortality_chance:
            #die
            sick_people[:,6][sick_people[:,0] == idx] = 3
            sick_people[:,10][sick_people[:,0] == idx] = 0
            died.append(np.int32(sick_people[sick_people[:,0] == idx][:,0][0]))
        else:
            #recover (become immune)
            sick_people[:,6][sick_people[:,0] == idx] = 2
            sick_people[:,10][sick_people[:,0] == idx] = 0
            cured.append(np.int32(sick_people[sick_people[:,0] == idx][:,0][0]))

    if len(died) > 0 and verbose:
        print('at timestep %i these people died: %s' %(frame, died))
    if len(cured) > 0 and verbose:
        print('at timestep %i these people recovered: %s' %(frame, cured))

    #put array back into population
    population[population[:,6] == 1] = sick_people

    return population


def compute_mortality(age, mortality_chance, risk_age=50,
                      critical_age=80, critical_mortality_chance=0.5,
                      risk_increase='linear'):

    '''compute mortality based on age

    The risk is computed based on the age, with the risk_age marking
    the age where risk starts increasing, and the crticial age marks where
    the 'critical_mortality_odds' become the new mortality chance.

    Whether risk increases linearly or quadratic is settable.

    Keyword arguments
    -----------------
    age : int
        the age of the person

    mortality_chance : float
        the base mortality chance
        can be very small but cannot be zero if increase is quadratic.

    risk_age : int
        the age from which risk starts increasing

    critical_age : int
        the age where mortality risk equals the specified 
        critical_mortality_odds

    critical_mortality_chance : float
        the odds of dying at the critical age

    risk_increase : str
        defines whether the mortality risk between the at risk age
        and the critical age increases linearly or exponentially
    '''

    if risk_age < age < critical_age: # if age in range
        if risk_increase == 'linear':
            #find linear risk
            step_increase = (critical_mortality_chance) / ((critical_age - risk_age) + 1)
            risk = critical_mortality_chance - ((critical_age - age) * step_increase)
            return risk
        elif risk_increase == 'quadratic':
            #define exponential function between risk_age and critical_age
            pw = 15
            A = np.exp(np.log(mortality_chance / critical_mortality_chance)/pw)
            a = ((risk_age - 1) - critical_age * A) / (A - 1)
            b = mortality_chance / ((risk_age -1) + a ) ** pw

            #define linespace
            x = np.linspace(0, critical_age, critical_age)
            #find values
            risk_values = ((x + a) ** pw) * b
            return risk_values[np.int32(age- 1)]
    elif age <= risk_age:
        #simply return the base mortality chance
        return mortality_chance
    elif age >= critical_age:
        #simply return the maximum mortality chance
        return critical_mortality_chance


def healthcare_infection_correction(worker_population, healthcare_risk_factor=0.2):
    '''corrects infection to healthcare population.

    Takes the healthcare risk factor and adjusts the sick healthcare workers
    by reducing (if < 0) ir increasing (if > 0) sick healthcare workers


    '''

    if healthcare_risk_factor < 0:
        #set 1 - healthcare_risk_factor workers to non sick
        sick_workers = worker_population[:,6][worker_population[:,6] == 1]
        cure_vector = np.random.uniform((len(sick_workers)))
        sick_workers[:,6][cure_vector >= healthcare_risk_factor] = 0
    elif healthcare_risk_factor > 0:
        #TODO: make proportion of extra workers sick
        pass
    else:
        pass #if no changed risk, do nothing

    return worker_population



def go_to_location(patient, destination, location_bounds, dest_no=1):
    '''sends patient to hospital

    '''

    x_center, y_center, x_wander, y_wander = get_motion_parameters(location_bounds[0],
                                                                   location_bounds[1],
                                                                   location_bounds[2],
                                                                   location_bounds[3])
    patient[13] = x_wander
    patient[14] = y_wander
    
    destination[(dest_no - 1) * 2] = x_center
    destination[((dest_no - 1) * 2) + 1] = y_center

    patient[11] = dest_no #set destination active

    return patient, destination