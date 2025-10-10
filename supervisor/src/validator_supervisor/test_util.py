import unittest

from .util import build_docker_image


class BuildDockerImageTest(unittest.IsolatedAsyncioTestCase):
    async def test_build_lighthouse(self):
        await build_docker_image('lighthouse', 'TEST')

    async def test_build_prysm(self):
        await build_docker_image('prysm', 'TEST')


if __name__ == '__main__':
    unittest.main()
