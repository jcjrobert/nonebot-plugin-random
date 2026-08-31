import setuptools

with open("README.md", "r", encoding="utf-8", errors="ignore") as f:
    long_description = f.read()
    setuptools.setup(
        name='nonebot-plugin-random',
        version='0.1.0',
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
        package_data={
            'nonebot-plugin-random': ['templates/*.html'],
        },
        python_requires='>=3.9.5',
        platforms="any",
        install_requires=[
            'nonebot2>=2.3.1',
            'nonebot-adapter-onebot>=2.4.3',
            'httpx>=0.27.0',
            'nonebot-plugin-htmlrender>=0.4.0',
            'nonebot-plugin-alconna>=0.51.4',
            'nonebot-plugin-waiter>=0.6.2',
            'Pillow>=10.3.0',
            'Jinja2>=3.1.4',
            'pydantic>=2.7.4',
        ],
    )
