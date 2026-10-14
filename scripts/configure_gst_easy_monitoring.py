"""Create or refresh the recorded preview dashboard; no alert recipients changed."""
import json
from pathlib import Path

import httpx

from deploy_v3 import gcloud,PROJECT


def main():
    deployment=json.loads(Path('artifacts/gst_easy/deployment.json').read_text())
    revisions=[next(row['revisionName'] for row in deployment[kind] if row.get('tag')=='gst-easy') for kind in ('api','web')]
    scope='resource.type="cloud_run_revision" AND ('+' OR '.join('resource.labels.revision_name="'+name+'"' for name in revisions)+')'
    widgets=[]
    for title,metric,aligner in [('Preview requests per second','run.googleapis.com/request_count','ALIGN_RATE'),
                                  ('Preview request latency p95 per series','run.googleapis.com/request_latencies','ALIGN_PERCENTILE_95')]:
        widgets.append({'title':title,'xyChart':{'dataSets':[{'timeSeriesQuery':{'timeSeriesFilter':{
            'filter':'metric.type="'+metric+'" AND '+scope,
            'aggregation':{'alignmentPeriod':'60s','perSeriesAligner':aligner}}},'plotType':'LINE'}],
            'yAxis':{'scale':'LINEAR'}}})
    dashboard={'displayName':'GST Easy isolated preview','gridLayout':{'columns':'2','widgets':widgets}}
    with httpx.Client(timeout=60,headers={'Authorization':'Bearer '+gcloud('auth','print-access-token').strip()}) as client:
        # Validate actual metric availability without printing credentials.
        for metric in ('run.googleapis.com/request_count','run.googleapis.com/request_latencies'):
            response=client.get(f'https://monitoring.googleapis.com/v3/projects/{PROJECT}/metricDescriptors/{metric}')
            response.raise_for_status()
        recorded=Path('artifacts/gst_easy/monitoring-dashboard.json')
        if recorded.exists():
            name=json.loads(recorded.read_text())['name']
            if not name.startswith(('projects/'+PROJECT+'/dashboards/', 'projects/624683933018/dashboards/')):
                raise RuntimeError('Recorded dashboard belongs to another project.')
            existing=client.get('https://monitoring.googleapis.com/v1/'+name)
            existing.raise_for_status()
            previous=existing.json()
            if previous.get('displayName')!=dashboard['displayName']:
                raise RuntimeError('Recorded dashboard identity changed; review before replacing.')
            dashboard.update(name=name,etag=previous['etag'])
            response=client.patch('https://monitoring.googleapis.com/v1/'+name,json=dashboard)
        else:
            response=client.post(f'https://monitoring.googleapis.com/v1/projects/{PROJECT}/dashboards',json=dashboard)
        response.raise_for_status()
        result=response.json()
    Path('artifacts/gst_easy/monitoring-dashboard.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'dashboard':result['name'],'preview_revisions':revisions,'notification_channels_changed':False}))


if __name__=='__main__':main()
