"""ABI loader with versioning and hash validation."""

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ABILoader:
    """Loads and validates contract ABIs with hash verification."""

    def __init__(self, abi_dir: str = "config/abis"):
        self.abi_dir = Path(abi_dir)
        self._loaded_abis: dict[str, list[dict]] = {}
        self._abi_hashes: dict[str, str] = {}

    def load_abi(self, name: str, expected_sha256: str = None) -> list[dict]:
        """Load ABI with optional hash validation.

        Args:
            name: ABI filename without extension
            expected_sha256: Expected SHA256 hash for validation

        Returns:
            ABI as list of dictionaries

        Raises:
            FileNotFoundError: If ABI file not found
            ValueError: If hash validation fails
        """
        if name in self._loaded_abis:
            return self._loaded_abis[name]

        abi_path = self.abi_dir / f"{name}.json"

        if not abi_path.exists():
            raise FileNotFoundError(f"ABI file not found: {abi_path}")

        try:
            with open(abi_path) as f:
                abi_content = f.read()

            # Validate hash if provided
            if expected_sha256:
                actual_hash = hashlib.sha256(abi_content.encode()).hexdigest()
                if actual_hash != expected_sha256:
                    raise ValueError(
                        f"ABI hash mismatch for {name}: expected {expected_sha256}, got {actual_hash}"
                    )

            parsed = json.loads(abi_content)
            # Support both plain ABI array and artifact JSON with top-level "abi" key
            abi = parsed.get("abi", parsed) if isinstance(parsed, dict) else parsed
            if not isinstance(abi, list):
                raise ValueError(
                    f"ABI for {name} is not a list (got {type(abi).__name__})"
                )
            self._loaded_abis[name] = abi
            self._abi_hashes[name] = hashlib.sha256(abi_content.encode()).hexdigest()

            logger.info(f"Loaded ABI {name} with hash {self._abi_hashes[name]}")
            return abi

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in ABI file {abi_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to load ABI {name}: {e}")
            raise

    def get_abi_hash(self, name: str) -> str:
        """Get SHA256 hash of loaded ABI.

        Args:
            name: ABI name

        Returns:
            SHA256 hash as hex string
        """
        if name not in self._abi_hashes:
            raise ValueError(f"ABI {name} not loaded")
        return self._abi_hashes[name]

    def list_available_abis(self) -> list[str]:
        """List all available ABI files.

        Returns:
            List of ABI names (without .json extension)
        """
        return [f.stem for f in self.abi_dir.glob("*.json")]

    def validate_all_abis(self, expected_hashes: dict[str, str]) -> dict[str, bool]:
        """Validate all ABIs against expected hashes.

        Args:
            expected_hashes: Dict mapping ABI names to expected SHA256 hashes

        Returns:
            Dict mapping ABI names to validation results
        """
        results = {}

        for name, expected_hash in expected_hashes.items():
            try:
                self.load_abi(name, expected_hash)
                results[name] = True
                logger.info(f"ABI {name} validation passed")
            except Exception as e:
                results[name] = False
                logger.error(f"ABI {name} validation failed: {e}")

        return results


# Global ABI loader instance
abi_loader = ABILoader()
