# Release validation

Target version: **1.0.0**. Status: **acceptance checks passed; approved for local release**.

## Acceptance checklist

| Area | Required evidence | Current status |
| --- | --- | --- |
| Backend | Full pytest suite, including authentication, expiry, security, results, concurrency, WebSockets, and maintenance safeguards | 204 passed |
| Frontend | Node tests, TypeScript checking, production build | 39 passed; build successful; npm audit reports 0 vulnerabilities |
| Fresh installation | Separate empty external volume; migrated catalog contains no polls or votes | Passed with a newly created volume |
| Full poll flows | Creation, voting, updates, exact results, closing/reopening for all three types | Passed through Nginx in an isolated installation |
| Public catalog | Combined filters, empty states, ordering, and privacy | Passed in the isolated and public installations |
| Persistence | Stop/start retains database contents | Passed; results and administrator session retained |
| Backup recovery | Real private archive restored into an isolated database and compared | Passed; all 6 public tables matched |
| Public access | HTTPS, WSS, administrator protection, disconnection behavior | HTTPS/WSS and denied anonymous access passed; previous tunnel disconnection test passed |
| Mobile and multiple devices | Mobile data, administrator login, creation, all types, live updates | Confirmed by the operator on 2026-11-05 |
| Physical reboot | PC restart preserves data and can resume operation | Confirmed by the operator on 2026-11-05 |
| Repository | No private configuration, archives, runtime database, or sample-data seed in distributed artifacts | No tracked archives/private environment files or configured secrets found; clean installation confirmed |
| Documentation | English installation, operation, security, architecture, recovery guides; no numbered-work-item filenames | Updated; local links validated |

## Known operational limits

- Anonymous tokens identify browser profiles, not people. Clearing storage can create another voter identity.
- Browser storage is required to recover a participant's vote.
- One API worker is required. Traffic quotas and WebSocket registries are process-local.
- Shared IPs share limits, including the simultaneous WebSocket cap.
- Quick Tunnel addresses change and provide no uptime guarantee. The host PC and Docker must remain available.
- Real keyboard, screen-reader, and mobile-network checks complement automated tests.

No critical defect may remain unresolved at release time. Do not treat a host HTTP request as proof of a mobile-network test or a container restart as proof of a physical PC reboot.

## Release procedure

1. Complete the checklist and record test totals and any fixes below.
2. Review `git diff --check`, `git diff`, and ignored/private files.
3. Obtain authorization for the final commit. Do not push or publish the repository automatically.
4. Only after every required check is confirmed and the final commit exists, create the local annotated tag:

   ```sh
   git tag -a v1.0.0 -m "VoteStupid 1.0.0"
   git show --no-patch v1.0.0
   ```

Never tag a dirty tree or mark missing operator checks as passed. GitHub publication and pushing the tag require separate authorization.

## Validation report

Validated on 2026-11-05:

- **204 backend tests** and **39 frontend tests** passed; the production build succeeded. npm audit reported zero vulnerabilities, including development dependencies.
- A separate Compose project and new external volume started with zero polls. The app and OpenAPI metadata both reported 1.0.0. No user volume or private configuration was copied into that installation.
- Each poll type completed creation, three independent votes, an update, exact results/percentages, closing/reopening, catalog notifications, and identical broadcasts to two independent WebSocket clients.
- Direct unauthorized creation/administration and incorrect individual tokens were rejected. Real session expiry and logout removed administrative access.
- A complete stop/start preserved all isolated results and an existing administrator session.
- A custom-format archive of the original database was restored into a new validation database. Ordered row fingerprints matched for all six public tables. Restoration into the populated original database was refused.
- The public candidate passed HTTPS, WSS, six state/type filter combinations, version information, and denied anonymous administration. Original voting data remains on the original local volume.
- Git contains no database archives or private environment files, and a scan against currently configured secrets found no matches in repository files. No archive/private-environment filenames were found in reachable Git history. Local backups remain private.

Corrections and preparation:

- Replaced incomplete, historical Spanish documents with English installation, operating, security, architecture, recovery, and release guides. Removed numbered-work-item documents.
- Added the missing first-install PostgreSQL password placeholder and Docker-only administrator hash generation support. Existing secrets were not changed.
- Added guarded backup/restore maintenance with six safety tests, binary-safe archives, and restoration into fresh validation targets.
- Unified backend API/OpenAPI and frontend package version metadata at 1.0.0, with a consistency regression test.
- Excluded database archive extensions from Git and Docker contexts. No startup sample-data import exists.
- Checked the backend application files and production frontend files inside the containers: no private environment files, configured secrets, or database archives were present.

At handoff, the public connector and all application containers exited cleanly with code 0. The public URL returned HTTP 530 after shutdown. An updated private pre-reboot archive was saved under `backups/`; real archives and all volumes were retained, while generated audit scripts and pytest temporary directories were removed. The isolated validation stack is also stopped.

The operator confirmed the final mobile-data and multi-device checks on 2026-11-05, including login, creation, voting/updates for all three types, closing/reopening, and live results.

The operator also confirmed the physical PC reboot check on 2026-11-05: the application restarted successfully and previous polls, results, and administrative access remained available.

No critical application defect remains known after the completed checks. **VoteStupid is ready for version 1.0.** The operator authorized the final commit and annotated local tag after confirming all acceptance checks. The tag must point to the reviewed release commit. Pushing or publishing to GitHub is not authorized as part of this local release.

### Finalization

Review and commit the release preparation, then create the annotated local `v1.0.0` tag only on the clean committed tree. Preserve private environment files, backups, and existing volumes. Publishing the repository or pushing commits/tags requires separate authorization.
