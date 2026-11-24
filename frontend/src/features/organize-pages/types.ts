export type PageSource = 'original' | 'added'

export type PageItem = {
  id: string
  source: PageSource
  page: number
  thumbnail: string
}

export type OrganizedResult = {
  url: string
  name: string
  size: number
}
