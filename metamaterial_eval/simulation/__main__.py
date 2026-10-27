"""Reproducible v0.6 preparation; never substitutes meshing for an ANSYS solve."""
import argparse
from dataclasses import replace
import hashlib
import importlib.metadata
import platform
from pathlib import Path
import sys
import time
from .config import CompressionConfig
from .geometry_adapter import authenticate_fixture
from .mesh_generation import generate_mesh, save_mesh
from .mesh_validation import validate_mesh, feature_resolution
from .reporting import write_json, mesh_hash, diagnostic_figures


def prepare_meshes(output, root, levels):
    output=Path(output)
    if output.exists():raise FileExistsError(f'Refusing to overwrite run: {output}')
    output.mkdir(parents=True)
    started=time.perf_counter()
    c=CompressionConfig()
    protocol=Path(root)/'experiments/pipeline_v0.6/protocol/PROTOCOL.json'
    write_json(output/'protocol_freeze.json',{'sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),
               'path':str(protocol.relative_to(root)), 'frozen_before_run':True})
    (output/'PROTOCOL.json').write_bytes(protocol.read_bytes())
    write_json(output/'environment.json',{'python':sys.version,'platform':platform.platform(),
               'packages':{n:importlib.metadata.version(n) for n in ['numpy','scipy','shapely','gmsh','matplotlib']}})
    try:
        geometry,mask,provenance=authenticate_fixture(root,c)
        write_json(output/'geometry_manifest.json',provenance)
        summaries=[]
        for index,size in enumerate(levels):
            c=replace(c,boundary_size=size)
            folder=output/f'level_{index:02d}';folder.mkdir()
            generated=folder/'generated';generated.mkdir()
            mesh=generate_mesh(geometry,c)
            save_mesh(mesh,generated/'mesh.npz')
            quality,distribution=validate_mesh(mesh,geometry,c)
            features=feature_resolution(mesh,provenance['source_only_solid_probes'],c)
            write_json(folder/'mesh_quality.json',quality)
            write_json(folder/'feature_resolution.json',features)
            manifest={'mesh_sha256':mesh_hash(mesh),'geometry_sha256':provenance['geometry_sha256'],
                      'config':c.manifest(),'mesh_gate':quality['accepted'],'feature_gate':features['accepted']}
            write_json(folder/'simulation_manifest.json',manifest)
            summaries.append({'level':index,'boundary_size_mm':size,**quality,
                              'sampled_features_accepted':features['accepted'],
                              'min_elements_across_sampled_chords':features['minimum_elements_across'],
                              'mesh_sha256':manifest['mesh_sha256']})
            print(f'Level {index}: {quality["nodes"]} nodes, {quality["elements"]} TRI6; mesh={quality["accepted"]}, sampled features={features["accepted"]}',flush=True)
            # A hard mesh failure is retained and stops subsequent stages.
            if not quality['accepted']:
                write_json(output/'FAILURE.json',{'stage':'mesh_quality','level':index,'gates':quality['gates']})
                break
        if summaries:
            diagnostic_figures(output/'figures',mesh,geometry,mask,distribution,c,provenance['source_only_solid_probes'])
        try:
            import resource
            peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
        except ImportError:peak=None
        write_json(output/'mesh_study.json',{'levels':summaries,'total_seconds':time.perf_counter()-started,
                   'process_peak_rss_bytes':peak,'memory_definition':'whole-process lifetime RSS high-water mark; not mesher-only allocation',
                   'mechanical_convergence':'NOT_EVALUATED_NO_ANSYS','peak_stress_convergence':'UNQUALIFIED'})
    except Exception as exc:
        write_json(output/'FAILURE.json',{'stage':'mesh_preparation','error':type(exc).__name__,'message':str(exc)})
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    mesh=commands.add_parser('mesh',help='Generate and validate source-authenticated meshes')
    mesh.add_argument('--boundary-sizes',type=float,nargs='+',default=[.01,.005,.01/3])
    pilot=commands.add_parser('input',help='Prepare a draft pilot input after revalidating its mesh')
    pilot.add_argument('--mesh-level',type=Path,required=True)
    commands.add_parser('benchmarks',help='Prepare analytical references and rectangle input bundles')
    solve=commands.add_parser('solve',help='Run an installed MAPDL executable; retain raw evidence')
    solve.add_argument('--input',type=Path,required=True)
    solve.add_argument('--executable',type=Path)
    solve.add_argument('--benchmark-evidence',type=Path)
    solve.add_argument('--timeout',type=float,default=3600)
    post=commands.add_parser('postprocess',help='Authenticate actual outputs, extract or quarantine')
    post.add_argument('--input',type=Path,required=True)
    for command in [mesh,pilot,commands.choices['benchmarks'],solve,post]:
        command.add_argument('--output',type=Path,required=True)
        command.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    args=parser.parse_args()
    if args.command=='mesh':prepare_meshes(args.output,args.root,args.boundary_sizes)
    elif args.command=='benchmarks':
        from .benchmarks import prepare_benchmarks
        prepare_benchmarks(args.output)
    elif args.command=='input':
        from .ansys_adapter import prepare_pilot_input
        prepare_pilot_input(args.mesh_level,args.output,args.root)
    elif args.command=='solve':
        import json
        from .solver_execution import execute
        evidence=None
        if args.benchmark_evidence:
            from .ansys_qualification import evidence_token
            content=json.loads(args.benchmark_evidence.read_text())
            evidence=evidence_token(args.benchmark_evidence) if content.get('schema')=='young-dawgs-v0.6.1-qualified-benchmark' else content
        status=execute(args.input,args.output,args.executable,args.timeout,evidence)
        print(status['status'])
        if status['status']!='EXECUTED_PENDING_IMPORT_CONTACT_AND_NUMERIC_VALIDATION':raise SystemExit(2)
    elif args.command=='postprocess':
        from .postprocessing import postprocess
        report=postprocess(args.input,args.output)
        print(report['status'])
        if report['status'].startswith('QUARANTINED'):raise SystemExit(2)


if __name__=='__main__':main()
