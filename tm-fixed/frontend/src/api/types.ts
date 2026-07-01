export type CreateJobResponse = { job_id: string }

export type ThumbnailVariants = {
  youtube: string
  shorts: string
  square: string
}

export type ThumbnailResponse = {
  id: string
  style_name: string
  imagekit_url: string | null
  status: string
  error_message: string | null
  variants?: ThumbnailVariants
}

export type JobResponse = {
  id: string
  prompt: string
  num_thumbnails: number
  headshot_url: string
  status: string
  thumbnails: ThumbnailResponse[]
}

