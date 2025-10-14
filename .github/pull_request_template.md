# Description

:)


# Pre-Merge Checklist

- [ ] I've tested my code and solemnly swear that it works flawlessly
- [ ] **For features, new functionality, or major refactors**: My changes are gated behind feature flag(s). 
  - Why? Feature flags allow us to continuously deploy new changes, but control if/when those changes actually go live in a Club Manager instance, and soft-revert changes if things don't work as expected. This means we don't need to keep a separate `develop` vs `main` branch.
  - Bug fixes should merge straight into `main` with no flags. 
  - Flags should default off. When your feature flag is disabled, Club Manager should behave as it did before your changes - as if your code does not exist. Database migrations should be fine to hang around.
  
  
