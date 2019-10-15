from opentrons import labware, instruments, modules, robot
from otcustomizers import StringSelection
import math

metadata = {
    'protocolName': 'QIAseq Targeted DNA Panel for Illumina Instruments Part 3:\
 Cleanup of adapter-ligated DNA',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request'
}

# load modules and labware
magdeck = modules.load('magdeck', '1')
rxn_plate = labware.load(
    'opentrons_96_aluminumblock_biorad_wellplate_200ul',
    '1',
    'reaction plate',
    share=True
)
elution_plate = labware.load(
    'opentrons_96_aluminumblock_biorad_wellplate_200ul', '2', 'elution plate')
reagent_reservoir = labware.load(
    'usascientific_12_reservoir_22ml', '3', 'reagent reservoir')

# reagents
nuc_free_water = reagent_reservoir.wells('A1')
beads = reagent_reservoir.wells('A2')
etoh = reagent_reservoir.wells('A3', length=4)
liquid_waste = [
    chan.top() for chan in reagent_reservoir.wells('A7', length=5)
]


def run_custom_protocol(
        number_of_samples: int = 96,
        p50_mount: StringSelection('right', 'left') = 'right',
        p300_mount: StringSelection('left', 'right') = 'left'
):
    # check
    if p50_mount == p300_mount:
        raise Exception('Input different mounts for pipettes.')

    num_sample_cols = math.ceil(number_of_samples/8)
    rxn_samples = rxn_plate.rows('A')[:num_sample_cols]
    elution_samples = elution_plate.rows('A')[:num_sample_cols]

    # pipettes
    tips300 = [labware.load('opentrons_96_tiprack_300ul', slot)
               for slot in ['4', '5', '6', '7']]
    tips50 = [labware.load('opentrons_96_tiprack_300ul', slot)
              for slot in ['8', '9', '10', '11']]

    m300 = instruments.P300_Multi(
        mount=p300_mount,
        tip_racks=tips300
    )
    m50 = instruments.P50_Multi(
        mount=p50_mount,
        tip_racks=tips50
    )

    tip50_count = 0
    tip300_count = 0
    tip50_max = len(tips50)*12
    tip300_max = len(tips300)*12

    def pick_up(pip):
        nonlocal tip50_count
        nonlocal tip300_count

        if pip == m50:
            if tip50_count == tip50_max:
                robot.pause('Replace 300ul tipracks before resuming.')
                m50.reset()
                tip50_count = 0
            m50.pick_up_tip()
            tip50_count += 1
        else:
            if tip300_count == tip300_max:
                robot.pause('Replace 300ul tipracks before resuming')
                m300.reset()
                tip300_count = 0
            m300.pick_up_tip()
            tip300_count += 1

    # distribute nuclease-free water and beads to each sample
    pick_up(m300)
    m300.distribute(
        50,
        nuc_free_water,
        [s.top() for s in rxn_samples],
        new_tip='never'
    )
    for s in rxn_samples:
        if not m300.tip_attached:
            pick_up(m300)
        m300.transfer(100, beads, s, new_tip='never')
        m300.mix(5, 100, s)
        m300.blow_out(s.top())
        m300.drop_tip()

    # incubate
    m300.delay(minutes=5)
    robot._driver.run_flag.wait()
    magdeck.engage(height=18)
    m300.delay(minutes=10)

    # remove supernatant
    for s in rxn_samples:
        pick_up(m300)
        m300.transfer(300, s, liquid_waste[0], new_tip='never')
        m300.drop_tip()

    # ethanol washes
    for wash in range(2):
        pick_up(m300)
        m300.transfer(
            200, etoh[wash], [s.top() for s in rxn_samples], new_tip='never')

        # remove supernatant
        for s in rxn_samples:
            if not m300.tip_attached:
                pick_up(m300)
            m300.transfer(300, s, liquid_waste[wash], new_tip='never')
            m300.drop_tip()

    # remove supernatant completely with P50 multi
    for s in rxn_samples:
        pick_up(m50)
        m50.transfer(50, s, liquid_waste[0], new_tip='never')
        m50.drop_tip()

    # airdry
    m50.delay(minutes=10)
    robot._driver.run_flag.wait()
    magdeck.disengage()

    for s in rxn_samples:
        pick_up(m300)
        m300.transfer(52, nuc_free_water, s, new_tip='never')
        m300.mix(5, 40, s)
        m300.blow_out(s.top())
        m300.drop_tip()

    magdeck.engage(height=18)
    robot.pause('Resume once the reaction solution has cleared.')

    # transfer to elution plate
    for s, d in zip(rxn_samples, elution_samples):
        pick_up(m50)
        m50.transfer(50, s, d, new_tip='never')
        m50.drop_tip()

    magdeck.disengage()
    robot.pause('Place elution plate on the magnetic deck.')

    # add beads and mix
    for s in rxn_samples:
        pick_up(m50)
        m50.transfer(50, beads, s, new_tip='never')
        m50.mix(5, 30, s)
        m50.blow_out(s.top())
        m50.drop_tip()

    m300.delay(minutes=5)
    robot._driver.run_flag.wait()
    magdeck.engage(height=18)
    m300.delay(minutes=5)

    # remove supernatant
    for s in rxn_samples:
        pick_up(m300)
        m300.transfer(300, s, liquid_waste[2], new_tip='never')
        m300.drop_tip()

    # ethanol washes
    for wash in range(2, 4):
        pick_up(m300)
        m300.transfer(
            200, etoh[wash], [s.top() for s in rxn_samples], new_tip='never')

        # remove supernatant
        for s in rxn_samples:
            if not m300.tip_attached:
                pick_up(m300)
            m300.transfer(300, s, liquid_waste[wash], new_tip='never')
            m300.drop_tip()

    # remove supernatant completely with P50 multi
    for s in rxn_samples:
        pick_up(m50)
        m50.transfer(50, s, liquid_waste[0], new_tip='never')
        m50.drop_tip()

    # airdry
    robot.pause('Allow beads to airdry for 15 minutes. Ensure beads are \
completely dry before resuming.')
    robot._driver.run_flag.wait()
    magdeck.disengage()

    for s in rxn_samples:
        pick_up(m50)
        m50.transfer(12, nuc_free_water, s, new_tip='never')
        m50.mix(5, 5, s)
        m50.blow_out(s.top())
        m50.drop_tip()

    magdeck.engage(height=18)
    robot.pause('Resume once the reaction solution has cleared. Place a fresh \
elution plate in slot 2.')

    # transfer to elution plate
    for s, d in zip(rxn_samples, elution_samples):
        pick_up(m50)
        m50.transfer(10, s, d, new_tip='never')
        m50.drop_tip()

    magdeck.disengage()
    robot.comment('Proceed with target enrichment. Alternatively, the samples \
can be stored at –20°C in a constant-temperature freezer for up to 3 days.')