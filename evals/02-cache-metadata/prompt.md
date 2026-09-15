---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
runs: 3
---
Review this block plugin for me.

`promo_tools/src/Plugin/Block/PromoBlock.php`
```php
<?php

namespace Drupal\promo_tools\Plugin\Block;

use Drupal\Core\Block\BlockBase;
use Drupal\Core\Cache\Cache;
use Drupal\Core\Plugin\ContainerFactoryPluginInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Session\AccountProxyInterface;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * @Block(
 *   id = "promo_block",
 *   admin_label = @Translation("Promotions")
 * )
 */
class PromoBlock extends BlockBase implements ContainerFactoryPluginInterface {

  protected $entityTypeManager;
  protected $currentUser;

  public function __construct(array $configuration, $plugin_id, $plugin_definition, EntityTypeManagerInterface $entity_type_manager, AccountProxyInterface $current_user) {
    parent::__construct($configuration, $plugin_id, $plugin_definition);
    $this->entityTypeManager = $entity_type_manager;
    $this->currentUser = $current_user;
  }

  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition) {
    return new static(
      $configuration,
      $plugin_id,
      $plugin_definition,
      $container->get('entity_type.manager'),
      $container->get('current_user')
    );
  }

  public function build() {
    $storage = $this->entityTypeManager->getStorage('node');

    $nids = $storage->getQuery()
      ->accessCheck(TRUE)
      ->condition('type', 'promotion')
      ->condition('status', 1)
      ->sort('created', 'DESC')
      ->range(0, 5)
      ->execute();

    $rows = [];
    $tags = [];
    foreach ($storage->loadMultiple($nids) as $node) {
      $rows[] = [
        'title' => $node->label(),
        'url' => $node->toUrl()->toString(),
      ];
      $tags[] = 'node:' . $node->id();
    }

    return [
      '#theme' => 'promo_list',
      '#rows' => $rows,
      '#show_codes' => $this->currentUser->hasPermission('view promo codes'),
      '#cache' => [
        'tags' => $tags,
        'contexts' => ['user'],
        'max-age' => Cache::PERMANENT,
      ],
    ];
  }

}
```
