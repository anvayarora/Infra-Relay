import * as Icons from 'lucide-react'
export function BlockIcon({name,className}:{name?:string;className?:string}){const Icon=(Icons as unknown as Record<string,React.ComponentType<{className?:string}>>)[name||'Boxes']||Icons.Boxes;return <Icon className={className}/>} 
