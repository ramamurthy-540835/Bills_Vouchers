import {NextRequest,NextResponse} from 'next/server'
export function proxy(request:NextRequest){
 if(!request.cookies.has('session'))return NextResponse.redirect(new URL('/login',request.url),302)
 return NextResponse.next()
}
export const config={matcher:['/','/documents/:path*','/gst/:path*','/search','/settings']}
