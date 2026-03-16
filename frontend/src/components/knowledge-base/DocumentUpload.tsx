import { useRef, useCallback } from 'react'
import { useDocuments } from '@/lib/hooks'
import { uploadDocument, deleteDocument } from '@/lib/api'
import { queryClient } from '@/lib/queryClient'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Upload, FileText, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800 animate-pulse',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

export function DocumentUpload({ kbId }: { kbId: string }) {
  const { data: docs } = useDocuments(kbId)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(
    async (files: FileList) => {
      for (const file of Array.from(files)) {
        try {
          await uploadDocument(kbId, file)
          queryClient.invalidateQueries({ queryKey: ['documents', kbId] })
          queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] })
          toast.success(`Uploaded ${file.name}`)
        } catch (err) {
          toast.error(err instanceof Error ? err.message : `Failed to upload ${file.name}`)
        }
      }
    },
    [kbId],
  )

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    if (e.dataTransfer.files.length) {
      handleFiles(e.dataTransfer.files)
    }
  }

  return (
    <div>
      <div
        className="flex cursor-pointer flex-col items-center gap-1 rounded-md border-2 border-dashed p-4 text-center transition-colors hover:border-primary/50 hover:bg-muted"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <Upload className="h-5 w-5 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">
          Drop files or click to upload
        </p>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,.txt"
          multiple
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
      </div>

      {docs && docs.length > 0 && (
        <ul className="mt-3 space-y-1">
          {docs.map((doc) => (
            <li key={doc.id} className="group flex items-center gap-2 text-sm">
              <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">{doc.filename}</span>
              <Badge variant="outline" className={`ml-auto shrink-0 text-xs ${STATUS_STYLES[doc.status]}`}>
                {doc.status}
              </Badge>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive"
                onClick={async () => {
                  try {
                    await deleteDocument(kbId, doc.id)
                    queryClient.invalidateQueries({ queryKey: ['documents', kbId] })
                    queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] })
                    toast.success(`Deleted ${doc.filename}`)
                  } catch {
                    toast.error(`Failed to delete ${doc.filename}`)
                  }
                }}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
