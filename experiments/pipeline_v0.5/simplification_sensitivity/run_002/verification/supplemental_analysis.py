"""Read-only analysis of completed B1 records; never generates or repairs candidates.

Run from the repository root with its recorded Python environment. Outputs are
supplemental diagnostics, separate from the prospectively frozen evaluator code.
"""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import shapely
from shapely import Point, box
from shapely.ops import nearest_points


OUTPUT = Path(__file__).resolve().parents[1]
ROOT = OUTPUT.parents[3]


def read(path):
    return json.loads(path.read_text())


def write(name, value):
    (OUTPUT / 'verification' / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def csv_write(name, rows):
    with (OUTPUT / 'summary' / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def boundary_plot(ax, geometry, color, origin, **kwargs):
    if geometry.is_empty:
        return
    if hasattr(geometry, 'geoms'):
        for part in geometry.geoms:
            boundary_plot(ax, part, color, origin, **kwargs)
    elif geometry.geom_type == 'Polygon':
        boundary_plot(ax, geometry.boundary, color, origin, **kwargs)
    elif geometry.geom_type in ('LineString', 'LinearRing'):
        xy = np.asarray(geometry.coords) - origin
        ax.plot(xy[:, 0], xy[:, 1], color=color, **kwargs)


def main():
    summary = read(OUTPUT / 'summary' / 'SIMPLIFICATION_SENSITIVITY.json')
    baselines = {b['fixture']: b for b in read(OUTPUT / 'baselines.json')['fixtures']}
    rows = [{**r, 'metrics': read(OUTPUT / r['metrics_file'])} for r in summary['candidates']]
    checks, necks, morphology, performance = [], [], [], []
    for r in rows:
        m = r['metrics']
        refs = baselines[r['fixture']]['provenance']['paths']
        candidate = shapely.from_wkb((OUTPUT / r['relative_directory'] / 'diagnostic_candidate.wkb').read_bytes())
        for comparison, source_name in [('distance_from_manifold', 'manifold'), ('distance_from_exact', 'exact')]:
            source = shapely.from_wkb((ROOT / refs[source_name]).read_bytes())
            for direction, target in [('source_to_target', candidate), ('target_to_source', source)]:
                item = m[comparison].get(direction)
                if not item or item.get('worst_sample_xy') is None:
                    continue
                point = Point(item['worst_sample_xy'])
                direct = point.distance(target.boundary)
                checks.append({'fixture': r['fixture'], 'role': r['study_role'], 'epsilon': r['epsilon'],
                               'comparison': comparison, 'direction': direction, 'point_xy': list(point.coords)[0],
                               'indexed_sample_distance': item['measured_max'], 'direct_GEOS_distance': direct,
                               'absolute_difference': abs(direct - item['measured_max'])})
        for kind in ('natural_necks', 'boundary_necks'):
            for n in m['features'].get(kind, []):
                necks.append({'fixture': r['fixture'], 'role': r['study_role'], 'epsilon': r['epsilon'],
                              'kind': kind, 'probe': n.get('probe_id', n.get('kind')),
                              'baseline_width': n.get('baseline_width'),
                              'candidate_width': n.get('candidate_chord', {}).get('width'),
                              'width_change': n.get('width_change'), 'narrowed': n.get('narrowed'),
                              'local_connected': n['local_solid_link']['connected'],
                              'local_symmetric_area': n['local_symmetric_difference_area'],
                              'boundary_measured_max': n['boundary_displacement']['measured_max'],
                              'connector_depths': json.dumps(n.get('candidate_depths'))})
        d = m.get('morphology', {}).get('comparison', {})
        for key, value in d.get('scalars', {}).items():
            morphology.append({'fixture': r['fixture'], 'role': r['study_role'], 'epsilon': r['epsilon'],
                               'kind': 'scalar', 'metric': key, 'baseline': value['reference'],
                               'candidate': value['candidate'], 'difference': value['difference'],
                               'relative_difference': value['relative_difference'], 'max_abs_curve_difference': None,
                               'curve_nrmse': None, 'exact_equal': value['exact_equal']})
        for key, value in d.get('curves', {}).items():
            morphology.append({'fixture': r['fixture'], 'role': r['study_role'], 'epsilon': r['epsilon'],
                               'kind': 'curve', 'metric': key, 'baseline': None, 'candidate': None,
                               'difference': None, 'relative_difference': None,
                               'max_abs_curve_difference': value['maximum_absolute_difference'],
                               'curve_nrmse': value['nrmse_reference_rms'], 'exact_equal': value['exact_equal']})
        performance.append({'fixture': r['fixture'], 'role': r['study_role'], 'epsilon': r['epsilon'],
                            **m['timing'], 'validation_peak_traced_bytes': m['validation_peak_traced_bytes'],
                            'simplification_peak_traced_bytes': m['simplification_peak_traced_bytes']})
    max_error = max(c['absolute_difference'] for c in checks)
    assert max_error <= 1e-10, max_error
    write('DIRECT_DISTANCE_CHECKS.json', {'definition': 'Saved worst sampled points checked using direct GEOS Point.distance(full opposing boundary), independently of the STRtree implementation. This verifies these points, not an exact continuous Hausdorff maximum.',
                                          'checks': checks, 'count': len(checks), 'maximum_absolute_difference': max_error, 'passed': True})
    csv_write('NECK_PROBES.csv', necks)
    csv_write('MORPHOLOGY_COMPARISONS.csv', morphology)
    # Timing dictionaries include the same stage keys for this entirely valid real sweep.
    csv_write('PERFORMANCE.csv', performance)
    old = OUTPUT.parent / 'run_001'
    old_summary = read(old / 'summary' / 'SIMPLIFICATION_SENSITIVITY.json')
    old_rows = {(r['fixture'], r['study_role'], r['epsilon']): r for r in old_summary['candidates']}
    comparisons = []
    for r in rows:
        prior = old_rows[(r['fixture'], r['study_role'], r['epsilon'])]
        om = read(old / prior['metrics_file'])
        comparisons.append({'fixture': r['fixture'], 'role': r['study_role'], 'epsilon': r['epsilon'],
                            'identical_candidate_WKB_hash': r['candidate_sha256'] == prior['candidate_sha256'],
                            'identical_raster_and_descriptor_measurements': all(r['metrics'][key] == om[key] for key in ('raster_from_canonical', 'raster_from_manifold')) and r['metrics']['morphology']['comparison'] == om['morphology']['comparison'],
                            'identical_continuous_area_and_distance': all(r['metrics'][key] == om[key] for key in ('area_from_manifold', 'area_from_exact', 'distance_from_manifold', 'distance_from_exact', 'continuous_topology'))})
    assert all(all(v for k, v in c.items() if k.startswith('identical_')) for c in comparisons)
    write('REPEATED_RUN_CHECK.json', {'comparison': comparisons, 'all_43_reproduce': True,
                                     'note': 'run_001 retained unchanged. run_002 corrects tri-valued aggregate reporting when fixed repair probes cannot be tracked. Candidate geometry, continuous measurements, rasters and frozen descriptor comparisons reproduce exactly.'})
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), layout='constrained')
    for ax, name in zip(axes.flat, baselines):
        for probe in ('natural_00', 'natural_01', 'natural_02'):
            data = sorted([n for n in necks if n['fixture'] == name and n['role'] == 'primary' and n['probe'] == probe], key=lambda n: n['epsilon'])
            ax.plot([n['epsilon'] for n in data], [100*n['width_change']/n['baseline_width'] if n['width_change'] is not None else np.nan for n in data], '.-', label=probe)
        ax.axhline(0, color='grey', lw=.6)
        ax.set(xlabel='ε (cell)', ylabel='Fixed normal-chord change (%)', title=name)
        ax.grid(alpha=.2)
    ax = axes.flat[-1]
    data = sorted([r for r in rows if r['fixture'] == 'design_009_seed_001' and r['study_role'] == 'primary'], key=lambda r: r['epsilon'])
    for i, x in enumerate((10.5, 11.5)):
        ax.plot([r['epsilon'] for r in data], [r['metrics']['features']['boundary_necks'][0]['candidate_depths'][i]['inward_solid_depth'] for r in data], '.-', label=f'x={x:g}')
    ax.axhline(5, color='grey', lw=.6)
    ax.set(xlabel='ε (cell)', ylabel='Inward solid depth (cell)', title='D9/S1 saved top connector')
    ax.grid(alpha=.2)
    axes.flat[0].legend(fontsize=8);ax.legend(fontsize=8)
    fig.suptitle('Monitored necks: geometric probes remain connected; widths can change\nThree selected natural probes per fixture are not exhaustive neck or mechanical qualification')
    fig.savefig(OUTPUT / 'figures' / '12_monitored_necks.png', dpi=220)
    plt.close(fig)
    selected = [r for r in rows if r['fixture'] == 'design_000_seed_000' and r['study_role'] == 'primary' and r['epsilon'] in (.5, .75, 1.)]
    source = shapely.from_wkb((ROOT / baselines['design_000_seed_000']['provenance']['paths']['manifold']).read_bytes())
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.8))
    for ax, r in zip(axes, selected):
        candidate = shapely.from_wkb((OUTPUT / r['relative_directory'] / 'diagnostic_candidate.wkb').read_bytes())
        d = r['metrics']['distance_from_manifold']['source_to_target']
        point = Point(d['worst_sample_xy']); origin = np.asarray(point.coords)[0]
        window = box(*(origin - 4), *(origin + 4))
        boundary_plot(ax, source.boundary.intersection(window), '#777777', origin, lw=1.2)
        boundary_plot(ax, candidate.boundary.intersection(window), '#0086bb', origin, lw=1.4)
        target = nearest_points(point, candidate.boundary)[1]
        xy = np.asarray([point.coords[0], target.coords[0]]) - origin
        ax.plot(xy[:, 0], xy[:, 1], '.-', color='#dd3b35', lw=2)
        ax.set(xlim=(-3, 3), ylim=(3, -3), xlabel='Δx (cell)', ylabel='Δy down (cell)',
               title=f"ε={r['epsilon']:g}; sampled distance={d['measured_max']:.6f}\nsource point ({origin[0]:.2f},{origin[1]:.2f})")
        ax.set_aspect('equal');ax.grid(alpha=.2)
    fig.suptitle('Independent displacement checks: grey=baseline, blue=candidate, red=nearest-boundary distance\nEach panel centers on its own saved source-to-candidate worst sampled point', fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, .87))
    fig.savefig(OUTPUT / 'figures' / '13_worst_sample_closeups.png', dpi=220, bbox_inches='tight')
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout='constrained')
    for i, (name, baseline) in enumerate(baselines.items()):
        if not baseline['registered_manifold_repairs']:
            continue
        data = sorted([r for r in rows if r['fixture'] == name and r['study_role'] == 'primary'], key=lambda r: r['epsilon'])
        color = f'C{i}'
        for contact in baseline['feature_definitions']['repairs']:
            values = [next(n['clearance'] for n in r['metrics']['features']['repairs'] if n['contact_id'] == contact['contact_id']) for r in data]
            axes[0].plot([r['epsilon'] for r in data], [np.nan if v is None else v for v in values], color=color, alpha=.25, lw=.8)
        axes[0].plot([r['epsilon'] for r in data], [r['metrics']['features']['minimum_repair_clearance'] for r in data], '.-', color=color, label=name)
        axes[1].plot([r['epsilon'] for r in data], [r['metrics']['features']['undefined_repair_clearance_count'] for r in data], '.-', color=color, label=name)
    axes[0].axhline(np.sqrt(2)/4, color='black', ls='--', lw=.8)
    axes[0].set(ylabel='Relevant separation (cell)', title='Defined per-contact and minimum separations')
    axes[1].set(ylabel='Contacts with undefined separation', title='Fixed void-anchor tracking unavailable')
    for ax in axes:
        ax.set(xlabel='ε (cell)', xlim=(-.025, 1.025));ax.grid(alpha=.2)
    axes[1].legend(fontsize=8)
    fig.suptitle('Repair clearance over the full sweep: ε=1 has no defined clearance for all 24 contacts\nUndefined tracking does not prove a new singularity; all primary boundaries remained manifold', fontsize=11)
    fig.savefig(OUTPUT / 'figures' / '14_repair_clearance_and_coverage.png', dpi=220, bbox_inches='tight')
    plt.close(fig)
    print(f'Independent distance checks: {len(checks)}, maximum discrepancy {max_error:g}; repeated 43 geometries and measurements match.')


if __name__ == '__main__':
    main()
