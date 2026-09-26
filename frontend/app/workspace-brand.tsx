import Image from 'next/image'
import Link from 'next/link'
import redTaxiLogo from './assets/red-taxi.png'

export default function WorkspaceBrand({clientId,legalName,placement='sidebar'}:{clientId?:string;legalName?:string;placement?:'sidebar'|'header'}){
 const redTaxi=clientId==='02f66f3a-0981-4db9-8bd3-1870855c4c09'||legalName?.trim().toLowerCase()==='red taxi'
 if(placement==='header')return redTaxi?<Link className="red-taxi-header-logo" href="/" aria-label="Red Taxi overview"><Image src={redTaxiLogo} alt="Red Taxi" width={122} height={66} unoptimized/></Link>:null
 return <Link className="bv-brand" href="/"><span className="brand-mark">bv.</span><span>Bills &amp; Vouchers<small>Clarity in every return</small></span></Link>
}
