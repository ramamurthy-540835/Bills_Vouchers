import {Layers,Files,Receipt,FileText,Building2,LifeBuoy,User,Settings,KeyRound,Shield,Search,MessageSquare} from 'lucide-react'
export type NavigationItem={id:string;label:string;route:string;icon:typeof Layers;permission:string;section:'workspace'|'account'|'administration'}
export const navigation:NavigationItem[]=[
 {id:'gstworkspace',label:'GST Easy',route:'/gst/workspace',icon:Layers,permission:'view_workspace',section:'workspace'},
 {id:'bills',label:'Bills & Vouchers',route:'/bills',icon:Files,permission:'view_workspace',section:'workspace'},
 {id:'filing',label:'Returns & Credit',route:'/gst/filing',icon:Receipt,permission:'view_workspace',section:'workspace'},
 {id:'reports',label:'Reports',route:'/reports',icon:FileText,permission:'view_reports',section:'workspace'},
 {id:'profile',label:'Business Profile',route:'/settings/profile',icon:Building2,permission:'view_workspace',section:'workspace'},
 {id:'search',label:'Search',route:'/search',icon:Search,permission:'view_workspace',section:'workspace'},
 {id:'assistant',label:'AI Assistant',route:'/assistant',icon:MessageSquare,permission:'view_workspace',section:'workspace'},
 {id:'help',label:'Help & Support',route:'/help',icon:LifeBuoy,permission:'manage_own_account',section:'workspace'},
 {id:'me',label:'My Profile',route:'/settings/me',icon:User,permission:'manage_own_account',section:'account'},
 {id:'account-business',label:'Business Profile',route:'/settings/profile',icon:Building2,permission:'view_workspace',section:'account'},
 {id:'account',label:'Account Settings',route:'/settings/account',icon:Settings,permission:'manage_own_account',section:'account'},
 {id:'password',label:'Change Password',route:'/settings/password',icon:KeyRound,permission:'manage_own_account',section:'account'},
 {id:'account-help',label:'Help & Support',route:'/help',icon:LifeBuoy,permission:'manage_own_account',section:'account'},
 {id:'administration',label:'Workspace Administration',route:'/admin/workspace',icon:Shield,permission:'platform_admin',section:'administration'},
]
export const canAccessMenuItem=(data:any,item:NavigationItem)=>Array.isArray(data?.permissions)&&data.permissions.includes(item.permission)
export const getVisibleNavigation=(data:any)=>navigation.filter(item=>item.section!=='account'&&!['profile','help'].includes(item.id)&&canAccessMenuItem(data,item))
export const getVisibleAccountMenu=(data:any)=>navigation.filter(item=>item.section==='account'&&canAccessMenuItem(data,item))

// Resolve destinations from fresh server permissions after the session has switched.
export function workspaceDestination(data:any, current:URL){
 const item=navigation.find(item=>item.route===current.pathname||(item.id==='reports'&&current.pathname.startsWith('/reports/')))
 const extra:Record<string,string>={'/settings/members':'manage_members','/settings/customers':'create_customer','/settings/onboarding':'edit_profile'}
 const allowed=item?canAccessMenuItem(data,item):Boolean(extra[current.pathname]&&data.permissions?.includes(extra[current.pathname]))
 const target=new URL(allowed?current.pathname:'/gst/workspace',current.origin)
 for(const key of ['period','scope','range']){const value=current.searchParams.get(key);if(value)target.searchParams.set(key,value)}
 return target.toString()
}
