import json
import pytest
from app.gst.intake import preview, parse


@pytest.mark.parametrize('source',['vendor','customer','driver'])
@pytest.mark.parametrize('count',[10,1000,10000])
def test_three_source_bulk_identity(source,count):
    rows=[{'source_record_id':str(i),'event_type':'trip' if source=='driver' else 'invoice',
           'source_version':'1','invoice_total':'118.00'} for i in range(count)]
    result=preview(source,parse(json.dumps(rows).encode(),'batch.json'))
    assert len(result['accepted'])==count and not result['errors']
    assert result['financial_records_created']==0


def test_duplicate_conflict_and_quarantine():
    row={'source_record_id':'1','event_type':'invoice','invoice_total':'118'}
    result=preview('vendor',[row,row,{**row,'invoice_total':'119'},{**row,'client_id':'foreign'}])
    assert len(result['accepted'])==1
    assert [e['status'] for e in result['errors']]==['duplicate','conflict','quarantined']


def test_mapping_and_limits():
    assert parse(b'ID,Kind\none,payment\n','x.csv',{'ID':'source_record_id','Kind':'event_type'})==[{'source_record_id':'one','event_type':'payment'}]
    with pytest.raises(ValueError):parse(b'[]','file.exe')
    with pytest.raises(ValueError):parse(json.dumps([{}]*10001).encode(),'x.json')
