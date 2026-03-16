import { useState, useRef, useEffect } from 'react'
import { useSkills } from '@/lib/hooks'
import { Button } from '@/components/ui/button'
import { Sparkles } from 'lucide-react'

interface SkillSelectorProps {
  selectedSkillId: string | null
  onSelect: (skillId: string | null) => void
}

export function SkillSelector({ selectedSkillId, onSelect }: SkillSelectorProps) {
  const { data: skills } = useSkills()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const selectedSkill = skills?.find((s) => s.id === selectedSkillId)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="gap-1.5 text-xs"
        onClick={() => setOpen(!open)}
      >
        <Sparkles className="h-3.5 w-3.5" />
        <span className="max-w-[100px] truncate">
          {selectedSkill ? selectedSkill.name : 'No Skill'}
        </span>
      </Button>

      {open && (
        <div className="absolute bottom-full left-0 z-50 mb-1 w-48 rounded-md border bg-popover p-1 shadow-md">
          <button
            className={`flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent ${
              !selectedSkillId ? 'bg-accent font-medium' : ''
            }`}
            onClick={() => {
              onSelect(null)
              setOpen(false)
            }}
          >
            No Skill
          </button>
          {skills?.map((skill) => (
            <button
              key={skill.id}
              className={`flex w-full items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent ${
                selectedSkillId === skill.id ? 'bg-accent font-medium' : ''
              }`}
              onClick={() => {
                onSelect(skill.id)
                setOpen(false)
              }}
            >
              <span className="truncate">{skill.name}</span>
            </button>
          ))}
          {(!skills || skills.length === 0) && (
            <p className="px-2 py-1.5 text-xs text-muted-foreground">
              No skills uploaded
            </p>
          )}
        </div>
      )}
    </div>
  )
}
