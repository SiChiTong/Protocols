import math

metadata = {
    'protocolName': 'Custom Chip PCR Preparation',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    num_samples, p10_mount, p50_mount = get_values(  # noqa: F821
        'num_samples', 'p10_mount', 'p50_mount')

    # check for too many samples
    if num_samples > 24:
        raise Exception("24 sample membranes maximum on chip.")
    if p10_mount == p50_mount:
        raise Exception('Pipette mounts cannot be the same.')

    # load labware
    tubes = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
        '1',
        '2ml Eppendorf snapcap reagent tubes'
    )
    chip = ctx.load_labware(
        'custom_24_shakerslide', '2', 'custom chip on shaker')
    strips = ctx.load_labware(
        'tempassure_96_strips_200ul_pcr', '3', 'PCR strips')
    tips10 = [
        ctx.load_labware('opentrons_96_tiprack_10ul', '4', '10ul tiprack')]
    tips50 = [
        ctx.load_labware('opentrons_96_tiprack_300ul', '5', '300ul tiprack')]

    # pipettes
    m10 = ctx.load_instrument(
        instrument_name='p10_multi',
        mount=p10_mount,
        tip_racks=tips10
    )
    p50 = ctx.load_instrument(
        instrument_name='p50_single',
        mount=p50_mount,
        tip_racks=tips50
    )

    if num_samples > 16:
        num_samples_for_mm = num_samples + 4
    else:
        num_samples = 20

    # reagents
    h2o = tubes.wells()[0]
    rxn_buffer = tubes.wells()[1]
    primer = tubes.wells()[2]
    dna_pol = tubes.wells()[3]
    mix_tube = tubes.wells()[4]

    # create master mix, enough for 4 extra samples
    p50.transfer(
        15.5*num_samples_for_mm,
        h2o,
        mix_tube.top(),
        blow_out=True
        )
    p50.transfer(
        5*num_samples_for_mm,
        rxn_buffer,
        mix_tube.top(),
        blow_out=True
        )
    if num_samples_for_mm > 10:
        p50.transfer(
            1*num_samples_for_mm,
            primer,
            mix_tube.top(),
            blow_out=True
        )

    p50.pick_up_tip()
    p50.transfer(
        0.25*num_samples_for_mm,
        dna_pol.bottom(),
        mix_tube,
        new_tip='never')
    p50.mix(10, 20, mix_tube)
    p50.blow_out(mix_tube.top())
    p50.drop_tip()

    # set up spots
    num_cols = math.ceil(num_samples/8)
    spots = [well for well in chip.rows()[0][:num_cols]]

    # slow flow rate and transfer sample to strips and immediately transfer
    # water to membrane
    m10.flow_rate.aspirate = 2
    m10.flow_rate.dispense = 2
    sample_strips = strips.rows()[0][:num_cols]
    h2o_strip = strips.rows()[0][-1]
    for spot, dest in zip(spots, sample_strips):
        # m10.transfer(8, spot.top(), dest, blow_out=True)
        m10.transfer(10, h2o_strip.bottom(1), spot.top(1))

    # transfer master mix to new strip tubes
    mix_wells = strips.wells()[24:24+num_samples]
    for m in mix_wells:
        p50.pick_up_tip()
        p50.transfer(21.75, mix_tube, m, new_tip='never')
        p50.blow_out(m.top(-3))
        p50.drop_tip()

    # reset flow rate to default and transfer sample to corresponding strip
    # tube already containing master mix
    m10.flow_rate.aspirate = 5
    m10.flow_rate.dispense = 10
    mix_strips = strips.rows()[0][3:6]
    for source, dest in zip(sample_strips, mix_strips):
        m10.pick_up_tip()
        m10.transfer(3, source, dest, new_tip='never')
        m10.mix(10, 9, dest)
        m10.drop_tip()
