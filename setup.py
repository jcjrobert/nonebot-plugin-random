import setuptools

with open("README.md", "r", encoding="utf-8", errors="ignore") as f:
    long_description = f.read()
    setuptools.setup(
        name='nonebot-plugin-random',
        version='0.0.5',
        author='jcjrobert',
        author_email='jcjrobbie@gmail.com',
        keywords=["pip", "nonebot2", "nonebot", "random", "抽图"],
        url='https://github.com/jcjrobert/nonebot-plugin-random',
        description='Nonebot2 通用抽图/语音插件',
        long_description=long_description,
        long_description_content_type="text/markdown",
        classifiers=[
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3',
        ],
        license='MIT License',
        packages=setuptools.find_packages(),
        include_package_data=True,
        platforms="any",
        install_requires=[
            'nonebot2>=2.0.0-beta.4', 'nonebot-adapter-onebot>=2.0.0-beta.4'
        ]
    )