from time import sleep

from modules.pv_api.Chemputer_Device_API import initialise_udp_keepalive, ChemputerPump, ChemputerValve

initialise_udp_keepalive(("192.168.255.255", 3000))
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s ; %(levelname)s ; %(message)s")

sleep(0.1)
# Initialize valves and pumps
pump1 = ChemputerPump("192.168.1.36")

valve1 = ChemputerValve("192.168.1.39")
valve2 = ChemputerValve("192.168.1.41")

# Clear errors and initialize hardware
pump1.clear_errors()
valve1.clear_errors()
valve2.clear_errors()
valve1.move_home()
valve1.wait_until_ready()
valve2.move_home()
valve2.wait_until_ready()
pump1.move_to_home(50)
pump1.wait_until_ready()

# postions of the valves
valve1_waste = 0
valve1_sample = 1
valve1_eluent_1 = 2
valve1_column_bottom = 3
valve1_eluent_2 = 4
valve1_eluent_3 = 5

valve2_waste = 0
valve2_collect_sample1 = 1
valve2_collect_sample2 = 2
valve2_collect_sample3 = 3
valve2_collect_sample4 = 4
valve2_collect_sample5 = 5


def run_column(volume, flow, source, output):
    '''
    Moves a given volume of the liquid from
    the source position and pumps it into the column.
    The output valve of the column is set to the output postion
    '''
    max_vol = 50.0
    pumped_vol = 0.0

    while pumped_vol < volume:
        if (volume - pumped_vol) < max_vol:
            avolume = (volume - pumped_vol)
        else:
            avolume = max_vol

        # Set the input valve position
        valve1.move_to_position(source)
        valve1.wait_until_ready()

        # Set the output valve position
        valve2.move_to_position(output)
        valve2.wait_until_ready()

        pump1.move_absolute(avolume, flow)
        pump1.wait_until_ready()

        valve1.move_to_position(valve1_column_bottom)
        valve1.wait_until_ready()

        pump1.move_absolute(0, flow)
        pump1.wait_until_ready()

        pumped_vol += avolume


if __name__ == '__main__':

    print('Starting the column')

    # Prime the column
    print('Primining th column')
    run_column(100, 25.0, valve1_eluent_1, valve2_waste)
    exit()

    print('Adding sample into column')

    # Add the sample into the column.
    run_column(30, 50.0, valve1_sample, valve2_waste)
    print('Adding 50 mL of hexane')

    # Develop the column
    run_column(50, 50.0, valve1_eluent_1, valve2_waste)

    eluent_added_volume = 0
    print('running the column with hexane/EA/TEA 500/500/20')
    for i in range(11):
        # Switch the solvent
        run_column(50, 50, valve1_eluent_3, valve2_collect_sample1)

        eluent_added_volume += 50
        print('Total added volome of eluent', eluent_added_volume)
        # input('Press enter to continue...')


    # collect the sample with Nytol free base to the second container
    eluent_added_volume = 0
    print('running the column with hexane/EA/TEA 500/500/20')
    for i in range(9):
        # Switch the solvent
        run_column(50, 50, valve1_eluent_3, valve2_collect_sample2)

        eluent_added_volume += 50
        print('Total added volome of eluent', eluent_added_volume)
        # input('Press enter to continue...')

    print('Finshed run')
