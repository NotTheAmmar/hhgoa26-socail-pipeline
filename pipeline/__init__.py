"""
Face ID & Blockchain Verification Pipeline
==========================================
Three-stage pipeline:
  1. face_detector     — detect & crop a face from an input image
  2. web_searcher      — reverse-image-search the face via Google Lens (SerpAPI)
                         and rank results by face similarity
  3. blockchain_verifier — hash & store the best match on a local EVM chain,
                           then re-verify tamper-evidence on-chain
"""
