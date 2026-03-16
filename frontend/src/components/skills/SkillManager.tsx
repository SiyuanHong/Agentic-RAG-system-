import { useRef } from 'react'
import { useSkills } from '@/lib/hooks'
import { uploadSkill, deleteSkill } from '@/lib/api'
import { queryClient } from '@/lib/queryClient'
import { Sparkles, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

export function SkillManager() {
  const { data: skills, isLoading } = useSkills()
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      await uploadSkill(file)
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      toast.success('Skill uploaded')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Upload failed')
    }
    // Reset input so the same file can be re-uploaded
    if (fileRef.current) fileRef.current.value = ''
  }

  async function handleDelete(skillId: string) {
    try {
      await deleteSkill(skillId)
      queryClient.invalidateQueries({ queryKey: ['skills'] })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  return (
    <div className="p-2">
      <div className="mb-2 flex items-center justify-between px-2">
        <span className="text-xs font-medium uppercase tracking-wider text-sidebar-foreground/60">
          Skills
        </span>
        <button
          onClick={() => fileRef.current?.click()}
          className="rounded p-1 hover:bg-sidebar-accent"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".md"
          className="hidden"
          onChange={handleUpload}
        />
      </div>

      {isLoading ? (
        <p className="px-2 text-sm text-sidebar-foreground/60">Loading...</p>
      ) : skills?.length === 0 ? (
        <p className="px-2 text-sm text-sidebar-foreground/60">None yet</p>
      ) : (
        skills?.map((skill) => (
          <div
            key={skill.id}
            className="group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm"
          >
            <Sparkles className="h-4 w-4 shrink-0 opacity-70" />
            <span className="truncate">{skill.name}</span>
            <button
              onClick={() => handleDelete(skill.id)}
              className="ml-auto hidden rounded p-0.5 hover:bg-sidebar-accent group-hover:block"
            >
              <Trash2 className="h-3.5 w-3.5 opacity-70" />
            </button>
          </div>
        ))
      )}
    </div>
  )
}
