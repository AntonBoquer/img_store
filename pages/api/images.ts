import { NextApiRequest, NextApiResponse } from 'next'
import { supabase } from '../../lib/supabase'

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method === 'GET') {
    try {
      const { data, error } = await supabase
        .from('images')
        .select('*')
        .order('created_at', { ascending: false })

      if (error) {
        console.error('Database error:', error)
        return res.status(500).json({ error: 'Failed to fetch images' })
      }

      return res.status(200).json({
        success: true,
        data,
      })
    } catch (error) {
      console.error('Server error:', error)
      return res.status(500).json({ error: 'Internal server error' })
    }
  }

  if (req.method === 'DELETE') {
    try {
      const { id } = req.query

      if (!id) {
        return res.status(400).json({ error: 'Image ID is required' })
      }

      // Get image data to delete from storage
      const { data: imageData, error: fetchError } = await supabase
        .from('images')
        .select('url')
        .eq('id', id)
        .single()

      if (fetchError) {
        return res.status(404).json({ error: 'Image not found' })
      }

      // Extract file path from URL
      const urlParts = imageData.url.split('/')
      const filePath = urlParts.slice(-2).join('/') // Get 'images/filename'

      // Delete from storage
      const { error: storageError } = await supabase.storage
        .from('images')
        .remove([filePath])

      if (storageError) {
        console.error('Storage deletion error:', storageError)
      }

      // Delete from database
      const { error: dbError } = await supabase
        .from('images')
        .delete()
        .eq('id', id)

      if (dbError) {
        console.error('Database deletion error:', dbError)
        return res.status(500).json({ error: 'Failed to delete image' })
      }

      return res.status(200).json({
        success: true,
        message: 'Image deleted successfully',
      })
    } catch (error) {
      console.error('Server error:', error)
      return res.status(500).json({ error: 'Internal server error' })
    }
  }

  return res.status(405).json({ error: 'Method not allowed' })
} 