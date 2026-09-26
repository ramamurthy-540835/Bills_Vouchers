from pathlib import Path

p = Path('frontend/app/workspace.tsx')
s = p.read_text(encoding='utf-8')
s = s.replace("import AccountMenu from './account-menu'", "import AccountMenu from './account-menu'\nimport GstEasyDashboard from './gst-easy-dashboard'\nimport BillsPanel from './bills/bills-panel'\nimport {GST} from '../lib/copy/gst'")
s = s.replace('documents:Files,', 'documents:Files,bills:Files,')
s = s.replace("['documents','/documents'", "['bills','/bills'")
s = s.replace("documents:'Documents',", "documents:GST.bills,bills:GST.bills,")
s = s.replace("{view==='gstworkspace'&&<GstWorkspace data={data} money={money}/>}", "{view==='gstworkspace'&&<GstEasyDashboard data={data} money={money}/>}")
s = s.replace("{view==='overview'&&<CustomerDashboard data={data} money={money}/>}", "{view==='overview'&&<GstEasyDashboard data={data} money={money}/>}{view==='bills'&&<BillsPanel data={data}/>}")
s = s.replace('</nav></aside>', '</nav><div className="sidebar-note">{GST.tagline}<small>{GST.process}</small></div></aside>')
s = s.replace('>Review GST workspace</Link>', '>{GST.name}</Link>')
p.write_text(s, encoding='utf-8')
