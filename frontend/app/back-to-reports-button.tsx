import Link from 'next/link'

export default function BackToReportsButton({period,range}:{period:string;range:string}) {
  return <Link className="report-back-button" href={{pathname:'/reports',query:{period,range}}}>
    {'\u2190'} Back to Reports
  </Link>
}
