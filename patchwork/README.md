# 1 描述
-------

| 脚本 | 描述 |
|:----:|:----:|
| get_patchwork_project.sh | 获取 patchwork 上所有的 project 列表(id 和 name 信息), 输出到 project/projects_list.md 中 |
| get_patchwork_series.sh | 获取 patchwork 上指定 project ID(-p 指定) 上指定日期(-d 指定) 的所有提交的补丁以及补丁集合 series. 输出到对应日期的目录中. |


# 2 get_patchwork_project.sh
-------


```cpp
bash ./get_patchwork_project.sh
cat project/projects_list.md
```

| ID | PROJECT |
|:--:|:-------:|
|  2  |  Linux ACPI  |
|  3  |  Linux SuperH Architecture mailing list  |
|  4  |  Linux V4L/DVB mailing list  |
|  5  |  Linux Kernel Build mailing list  |
|  6  |  Device Mapper Development  |
|  7  |  CIFS (Samba) Client  |
|  8  |  KVM development  |
|  9  |  Linux Sparse mailing list  |
|  10  |  Linux ARM based TI OMAP SoCs mailing list  |
|  11  |  Linux PA-RISC based architecture mailing list  |
|  12  |  Linux PCI development list  |
|  13  |  Linux DaVinci SOCs  |
|  14  |  Intel Graphics Driver  |
|  15  |  Linux Wireless Mailing List  |
|  16  |  V9FS (Plan 9) Filesystem Development Mailing List  |
|  17  |  Linux Input Mailing List  |
|  18  |  Linux RDMA and InfiniBand  |
|  19  |  Linux BTRFS  |
|  20  |  Linux SPI core/device drivers discussion  |
|  21  |  DRI Development  |
|  22  |  CEPH development  |
|  32  |  Linux MMC development  |
|  41  |  Linux NFS mailing list  |
|  51  |  Linux framebuffer layer  |
|  61  |  Linux power management  |
|  62  |  Linux ARM Kernel Architecture  |
|  71  |  LTSI Project development  |
|  81  |  Linux Samsung SOC mailing list  |
|  91  |  OCFS2 Development  |
|  92  |  Linux ARM MSM sub-architecture  |
|  111  |  Linux DMAEngine  |
|  121  |  ALSA development  |
|  131  |  Rockchip SoC list  |
|  141  |  FSTests  |
|  151  |  Linux Crypto  |
|  161  |  DASH shell  |
|  171  |  TPM Device Driver list  |
|  181  |  ath10k  |
|  191  |  NVDIMM support in Linux  |
|  201  |  Linux FS Development  |
|  211  |  Discussions and development of Linux SCSI subsystem  |
|  221  |  Linux-Mediatek patches  |
|  231  |  x86 platform driver layer  |
|  241  |  Linux Block  |
|  251  |  Linux Audit  |
|  261  |  SELinux Development list  |
|  271  |  WPAN under Linux  |
|  281  |  XEN Development list  |
|  291  |  Linux Renesas SoC patches  |
|  301  |  QEMU patches  |
|  311  |  Linux HWMON  |
|  321  |  Linux Modules  |
|  331  |  Linux Clock framework  |
|  333  |  Security modules development  |
|  335  |  Linux Hardening  |
|  337  |  Linux amlogic  |
|  339  |  XFS devel  |
|  341  |  Linux Remoteproc  |
|  343  |  Linux Oxnas  |
|  345  |  Linux FPGA development  |
|  347  |  Intel SGX  |
|  349  |  Linux Backports  |
|  351  |  SCSI target development list  |
|  353  |  Linux fscrypt  |
|  355  |  Libteam  |
|  357  |  Linux Integrity  |
|  359  |  Linux IIO  |
|  361  |  Linux MLXSW  |
|  363  |  Linux USB  |
|  365  |  Linux MM  |
|  367  |  Kernel Selftest  |
|  369  |  Lustre software development  |
|  371  |  Git SCM  |
|  373  |  CIP Project Development  |
|  377  |  Linux RISC-V  |
|  379  |  Linux SoC  |
|  381  |  Linux MIPS  |
|  383  |  Linux I3C  |
|  385  |  Linux-Trace Development  |
|  387  |  Linux Watchdog Development  |
|  389  |  ath11k  |
|  391  |  Linux EDAC  |
|  393  |  Linux Keyrings  |
|  395  |  Bluetooth  |
|  397  |  Linux Safety  |
|  399  |  Netdev + BPF  |
|  401  |  Linux PHY  |
|  403  |  CXL  |
|  405  |  MPTCP  |

# 3 get_patchwork_series.sh
-------

```cpp
bash get_patchwork_series.sh -p 365 -d 2022-01-24
cat 2022-01-24/2022-01-24.md
```

| 时间  | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |
|:-----:|:----:|:----:|:----:|:------------:|:----:|
| 2022/01/24} | liupeng (DM) <liupeng256@huawei.com> | [Add a module parameter to adjust kfence objects](https://patchwork.kernel.org/project/linux-mm/cover/20220124025205.329752-1-liupeng256@huawei.com/) | 607689 | v1 ☐☑ | [PatchWork v1,0/3](https://lore.kernel.org/r/20220124025205.329752-1-liupeng256@huawei.com) |
| 2022/01/24} | NeilBrown <neilb@suse.de> | [Repair SWAP-over_NFS](https://patchwork.kernel.org/project/linux-mm/cover/164299573337.26253.7538614611220034049.stgit@noble.brown/) | 607709 | v3 ☐☑ | [PatchWork v3,0/23](https://lore.kernel.org/r/164299573337.26253.7538614611220034049.stgit@noble.brown) |
| 2022/01/24} | Muchun Song <songmuchun@bytedance.com> | [[v2,1/2] mm: thp: fix wrong cache flush in remove_migration_pmd()](https://patchwork.kernel.org/project/linux-mm/patch/20220124051752.83281-1-songmuchun@bytedance.com/) | 607714 | v2 ☐☑ | [PatchWork v2,0/2](https://lore.kernel.org/r/20220124051752.83281-1-songmuchun@bytedance.com) |
| 2022/01/24} | Christophe Leroy <christophe.leroy@csgroup.eu> | [Allocate module text and data separately](https://patchwork.kernel.org/project/linux-mm/cover/cover.1643015752.git.christophe.leroy@csgroup.eu/) | 607770 | v1 ☐☑ | [PatchWork v1,0/7](https://lore.kernel.org/r/cover.1643015752.git.christophe.leroy@csgroup.eu) |
| 2022/01/24} | Anshuman Khandual <anshuman.khandual@arm.com> | [mm/mmap: Drop protection_map[] and platform's __SXXX/__PXXX requirements](https://patchwork.kernel.org/project/linux-mm/cover/1643029028-12710-1-git-send-email-anshuman.khandual@arm.com/) | 607842 | v1 ☐☑ | [PatchWork v1,0/31](https://lore.kernel.org/r/1643029028-12710-1-git-send-email-anshuman.khandual@arm.com) |
| 2022/01/24} | Miaohe Lin <linmiaohe@huawei.com> | [mm/vmalloc: remove unneeded function forward declaration](https://patchwork.kernel.org/project/linux-mm/patch/20220124133752.60663-1-linmiaohe@huawei.com/) | 607865 | v1 ☐☑ | [PatchWork v1,0/1](https://lore.kernel.org/r/20220124133752.60663-1-linmiaohe@huawei.com) |
| 2022/01/24} | Marco Elver <elver@google.com> | [kasan: test: fix compatibility with FORTIFY_SOURCE](https://patchwork.kernel.org/project/linux-mm/patch/20220124160744.1244685-1-elver@google.com/) | 607913 | v1 ☐☑ | [PatchWork v1,0/1](https://lore.kernel.org/r/20220124160744.1244685-1-elver@google.com) |
| 2022/01/24} | Ard Biesheuvel <ardb@kernel.org> | [mm: make 'highmem' symbol ro_after_init](https://patchwork.kernel.org/project/linux-mm/patch/20220124170555.1054480-1-ardb@kernel.org/) | 607949 | v1 ☐☑ | [PatchWork v1,0/1](https://lore.kernel.org/r/20220124170555.1054480-1-ardb@kernel.org) |
| 2022/01/24} | Zi Yan <zi.yan@sent.com> | [mm: page_alloc: avoid merging non-fallbackable pageblocks with others.](https://patchwork.kernel.org/project/linux-mm/patch/20220124175957.1261961-1-zi.yan@sent.com/) | 608000 | v1 ☐☑ | [PatchWork v1,0/1](https://lore.kernel.org/r/20220124175957.1261961-1-zi.yan@sent.com) |
| 2022/01/24} | andrey.konovalov@linux.dev <andrey.konovalov@linux.dev> | [kasan, vmalloc, arm64: add vmalloc tagging support for SW/HW_TAGS](https://patchwork.kernel.org/project/linux-mm/cover/cover.1643047180.git.andreyknvl@google.com/) | 608001 | v6 ☐☑ | [PatchWork v6,0/39](https://lore.kernel.org/r/cover.1643047180.git.andreyknvl@google.com) |
